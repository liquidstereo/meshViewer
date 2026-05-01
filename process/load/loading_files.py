import os
import sys
import time
import hashlib
import logging
import subprocess
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

from process.load.memory_guard import (
    release_process_memory, evict_file_cache,
)
from process.load.load_mesh import read_polydata
from process.load.load_pointcloud import (
    is_gs_ply, build_gs_npz_cache, load_gs_frame, pack_pt_colors,
    GS_CACHE_FILE,
)

import numpy as np
import pyvista as pv
from alive_progress import alive_bar

import psutil

from configs.settings import (
    DEFAULT_PRELOAD_ALL,
    DEFAULT_WINDOW_SIZE, DEFAULT_PRELOAD_AHEAD,
    PRELOAD_BACK_RATIO, EVICT_MEMORY_THRESHOLD,
    WORKER_COUNT, CACHE_DIR_ROOT, TEX_EXTENSIONS,
    TEXTURE_DIR_ROOT,
    AUTO_DECIMATE_THRESHOLD, AUTO_DECIMATE_MAX_CELLS, AUTO_DECIMATE_MAX_RATIO,
    PT_SUBSAMPLE_THRESHOLD, PT_SUBSAMPLE_TARGET,
    NP_SUBSAMPLE_THRESHOLD, NP_SUBSAMPLE_TARGET,
)
from process.utils.extract_texture import extract_embedded_texture

logger = logging.getLogger(__name__)

_CACHE_WORKER_TIMEOUT = 60

_EVICT_RELEASE_INTERVAL = 2.0

_NPY_EXT = '.npy'
_NPZ_INPUT_EXT = '.npz'

def _dispatch_cache_build(obj_path: str, npz_dir: str) -> None:
    if is_gs_ply(obj_path):
        frame_dir = _frame_cache_dir(obj_path, npz_dir)
        build_gs_npz_cache(obj_path, frame_dir)
    elif os.path.splitext(obj_path)[1].lower() in (
        _NPY_EXT, _NPZ_INPUT_EXT
    ):
        _build_single_npz(obj_path, npz_dir)
    else:
        _build_one_subprocess(obj_path, npz_dir)

def _check_preload_feasible(
    obj_files: list,
    npz_dir: str,
    safety: float = 0.70,
) -> bool:
    if not obj_files:
        return True
    frame_dir = _frame_cache_dir(obj_files[0], npz_dir)
    try:
        gs_path = os.path.join(frame_dir, GS_CACHE_FILE)
        if os.path.exists(gs_path):
            d = np.load(gs_path)
            n_pts = d['xyz'].shape[0]
            est_mb = n_pts * 15 / (1024 ** 2) * 2.5
        else:
            pts_path = os.path.join(frame_dir, 'points.npy')
            if not os.path.exists(pts_path):
                return True
            est_mb = os.path.getsize(pts_path) / (1024 ** 2) * 2.5
    except Exception:
        return True
    total_est_mb = len(obj_files) * est_mb
    avail_mb = psutil.virtual_memory().available / (1024 ** 2)
    logger.info(
        'Preload feasibility check: est %.0fMB vs avail %.0fMB'
        ' (threshold %.0f%%).',
        total_est_mb, avail_mb, safety * 100,
    )
    if total_est_mb > avail_mb * safety:
        logger.warning(
            'Preload-all disabled: est %.0fMB > %.0f%% avail (%.0fMB).'
            ' Switching to sliding window.',
            total_est_mb, safety * 100, avail_mb,
        )
        return False
    return True

def _build_one_subprocess(obj_path: str, npz_dir: str) -> None:
    env = os.environ.copy()
    env['OMP_NUM_THREADS'] = '1'
    proc = subprocess.Popen(
        [
            sys.executable, '-m',
            'process.load._cache_worker',
            obj_path, npz_dir,
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        env=env,
    )
    try:
        _, stderr = proc.communicate(timeout=_CACHE_WORKER_TIMEOUT)
        if proc.returncode != 0:
            msg = stderr.decode(errors='replace').strip()
            raise RuntimeError(msg)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.communicate()
        raise RuntimeError(
            f'VTK hang timeout ({_CACHE_WORKER_TIMEOUT}s):'
            f' {os.path.basename(obj_path)}'
        )

def _frame_cache_dir(obj_path: str, npz_dir: str) -> str:
    name = os.path.basename(obj_path)
    base, ext = os.path.splitext(name)
    return os.path.join(npz_dir, f'{base}_{ext[1:]}')

def _is_cache_stale(src_path: str, frame_dir: str) -> bool:
    for fname in (GS_CACHE_FILE, 'points.npy'):
        sentinel = os.path.join(frame_dir, fname)
        if os.path.exists(sentinel):
            return os.path.getmtime(src_path) > os.path.getmtime(sentinel)
    return True

def _build_single_npz(obj_path: str, npz_dir: str) -> None:
    if is_gs_ply(obj_path):
        frame_dir = _frame_cache_dir(obj_path, npz_dir)
        build_gs_npz_cache(obj_path, frame_dir)
        return
    try:
        mesh = read_polydata(obj_path)
        frame_dir = _frame_cache_dir(obj_path, npz_dir)
        os.makedirs(frame_dir, exist_ok=True)
        if mesh.faces.size > 0:
            faces = mesh.faces
            if int(faces.max()) < np.iinfo(np.int32).max:
                faces = faces.astype(np.int32)
            _p = os.path.join(frame_dir, 'faces.npy')
            np.save(_p, faces)
            evict_file_cache(_p)
        for key in mesh.point_data.keys():
            _p = os.path.join(frame_dir, f'pd_{key}.npy')
            np.save(_p, mesh.point_data[key])
            evict_file_cache(_p)
        tc = mesh.active_texture_coordinates
        if tc is not None:
            _p = os.path.join(frame_dir, 'tcoords.npy')
            np.save(_p, tc)
            evict_file_cache(_p)

        _p = os.path.join(frame_dir, 'points.npy')
        np.save(_p, mesh.points)
        evict_file_cache(_p)
    except Exception as e:
        logger.error('Frame cache build failed [%s]: %s', obj_path, e)
        raise

def _load_mesh_frame(frame_dir: str) -> pv.PolyData:
    if os.path.exists(os.path.join(frame_dir, GS_CACHE_FILE)):
        return load_gs_frame(frame_dir)
    pts = np.array(
        np.load(os.path.join(frame_dir, 'points.npy'), mmap_mode='r')
    )
    faces_path = os.path.join(frame_dir, 'faces.npy')
    faces = (
        np.array(np.load(faces_path, mmap_mode='r'))
        if os.path.exists(faces_path) else None
    )
    mesh = pv.PolyData(pts, faces)
    for fname in sorted(os.listdir(frame_dir)):
        if not (fname.startswith('pd_') and fname.endswith('.npy')):
            continue
        key = fname[3:-4]
        mesh.point_data[key] = np.array(
            np.load(os.path.join(frame_dir, fname), mmap_mode='r')
        )
    tc_path = os.path.join(frame_dir, 'tcoords.npy')
    if os.path.exists(tc_path):
        mesh.active_texture_coordinates = np.array(
            np.load(tc_path, mmap_mode='r')
        )
    return mesh

class FrameBuffer:

    def __init__(
        self,
        obj_files: list,
        smooth: bool,
        preload_all: bool = DEFAULT_PRELOAD_ALL,
        window_size: int = DEFAULT_WINDOW_SIZE,
        preload_ahead: int = DEFAULT_PRELOAD_AHEAD,
        no_cache: bool = False,
    ):
        self._obj_files = obj_files
        self._smooth = smooth
        self._preload_all = preload_all
        self._window_size = window_size
        self._preload_ahead = preload_ahead
        self._no_cache = no_cache
        self._mesh_cache = {}
        self._tex_cache = {}
        self._lock = threading.Lock()
        _eff_workers = WORKER_COUNT if len(obj_files) >= 4 else 1
        self._mesh_executor = ThreadPoolExecutor(
            max_workers=_eff_workers
        )
        self._tex_executor = ThreadPoolExecutor(
            max_workers=_eff_workers
        )
        self._pending_mesh = set()
        self._pending_tex = set()
        self._last_evict_release = 0.0

        input_dir = os.path.dirname(obj_files[0])
        if len(obj_files) == 1:
            self._input_name = os.path.splitext(
                os.path.basename(obj_files[0])
            )[0]
        else:
            self._input_name = os.path.basename(input_dir)
        _dir_hash = hashlib.md5(
            os.path.abspath(input_dir).encode()
        ).hexdigest()[:8]
        self._npz_dir = os.path.join(
            CACHE_DIR_ROOT, f'{self._input_name}_{_dir_hash}'
        )
        self._tex_dir = os.path.join(
            TEXTURE_DIR_ROOT, self._input_name
        )
        _tex_path = self._find_shared_texture()
        self._shared_tex = None
        tex_needed = _tex_path is None
        npz_needed = not self._no_cache

        if _tex_path and npz_needed:
            logger.info('Starting parallel: texture load + NPZ build.')
            with ThreadPoolExecutor(max_workers=2) as exe:
                tex_fut = exe.submit(self._load_tex_from_path, _tex_path)
                npz_fut = exe.submit(self._ensure_npz_cache)
                self._shared_tex = tex_fut.result()
                npz_fut.result()
        elif _tex_path:
            self._shared_tex = self._load_tex_from_path(_tex_path)
        elif tex_needed and npz_needed:

            self._ensure_npz_cache()
            extracted = extract_embedded_texture(
                obj_files[0], self._tex_dir, self._input_name,
            )
            if extracted is not None:
                self._shared_tex = self._load_tex_from_path(extracted)
        elif tex_needed:
            extracted = extract_embedded_texture(
                obj_files[0], self._tex_dir, self._input_name,
            )
            if extracted is not None:
                self._shared_tex = self._load_tex_from_path(extracted)
        else:
            if npz_needed:
                self._ensure_npz_cache()
        if self._preload_all and not self._no_cache:
            self._preload_all = _check_preload_feasible(
                self._obj_files, self._npz_dir
            )
        if self._preload_all:
            _tex_futs = self._submit_tex_futs()
            self._preload_all_meshes()
            self._preload_all_textures(_tex_futs)
        else:
            self._warm_start()

    @property
    def total(self) -> int:
        return len(self._obj_files)

    @property
    def max_points(self) -> int:
        return getattr(self, '_max_points', 0)

    @property
    def first_frame(self) -> tuple:
        return self.get(0)

    def get(self, idx: int) -> tuple:
        mesh = self._get_mesh(idx)
        with self._lock:
            tex = self._tex_cache.get(idx)
        return mesh, tex

    def notify(self, idx: int) -> None:
        self._prefetch(idx)
        self._evict(idx)

    def cleanup(self) -> None:
        self._mesh_executor.shutdown(wait=False)
        self._tex_executor.shutdown(wait=False)
        with self._lock:
            self._mesh_cache.clear()
            self._tex_cache.clear()
            self._pending_mesh.clear()
            self._pending_tex.clear()
        release_process_memory('cleanup')
        logger.info('FrameBuffer cleanup COMPLETE')

    def _preload_all_meshes(self) -> None:
        total = self.total
        logger.info('Preloading all %d meshes...', total)
        t0 = time.perf_counter()
        try:
            with alive_bar(
                total, spinner=None,
                title='PRELOADING MESH FILES...',
                title_length=25, length=15,
                stats=True, elapsed=True,
                manual=False, enrich_print=True,
                force_tty=True
            ) as bar:
                if total == 1:
                    mesh = self._load_mesh(0)
                    with self._lock:
                        self._mesh_cache[0] = mesh
                    bar()
                else:
                    futs = {
                        self._mesh_executor.submit(
                            self._load_mesh, i
                        ): i
                        for i in range(total)
                    }
                    for fut in as_completed(futs):
                        idx = futs[fut]
                        try:
                            mesh = fut.result()
                        except Exception as e:
                            logger.error(
                                'Preload failed [idx=%d]: %s', idx, e
                            )
                            mesh = pv.PolyData()
                        with self._lock:
                            self._mesh_cache[idx] = mesh
                        bar()
                bar.title = 'MESH PRELOADING COMPLETE'
        except KeyboardInterrupt:
            logger.warning('Mesh file preload interrupted.')
            self.cleanup()
            raise
        logger.info(
            'All %d meshes preloaded in %.2fs.',
            total, time.perf_counter() - t0,
        )
        release_process_memory('preload_complete')
        self._max_points = 0
        with self._lock:
            vals = list(self._mesh_cache.values())
        if vals and all(m.n_faces_strict == 0 for m in vals):
            self._max_points = max(m.n_points for m in vals)
            logger.debug('PT max_points: %d', self._max_points)

    def _find_shared_texture(self) -> 'str | None':
        found_in_subdir = None
        found_in_root = None

        for ext in TEX_EXTENSIONS:
            if found_in_subdir is None:
                p1 = os.path.join(
                    self._tex_dir, self._input_name + ext
                )
                if os.path.exists(p1):
                    found_in_subdir = p1

            if found_in_root is None:
                p2 = os.path.join(
                    TEXTURE_DIR_ROOT, self._input_name + ext
                )
                if os.path.exists(p2):
                    found_in_root = p2

        if found_in_subdir and found_in_root:
            raise ValueError(
                f'Ambiguous texture: both "{found_in_subdir}"'
                f' and "{found_in_root}" exist.'
                ' Remove one to resolve the conflict.'
            )

        t_path = found_in_subdir or found_in_root
        if t_path is None:
            return None

        logger.info('Shared texture found: %s', t_path)
        return t_path

    def _load_tex_from_path(self, t_path: str) -> 'pv.Texture':
        t0 = time.perf_counter()
        tex = pv.read_texture(t_path)
        logger.info(
            'Texture loaded: %s in %.4fs', t_path,
            time.perf_counter() - t0,
        )
        return tex

    def _submit_tex_futs(self) -> 'dict | None':
        if not os.path.isdir(self._tex_dir):
            return None
        if self._shared_tex is not None:
            return None
        logger.info(
            'Pre-submitting %d texture futures '
            '(parallel with mesh preload).',
            self.total,
        )
        return {
            self._tex_executor.submit(
                self._load_texture, i
            ): i
            for i in range(self.total)
        }

    def _preload_all_textures(
        self, tex_futs: 'dict | None' = None
    ) -> None:
        if self._shared_tex is not None:
            with self._lock:
                for i in range(self.total):
                    self._tex_cache[i] = self._shared_tex
            logger.info(
                'Shared texture applied to all %d frames.',
                self.total,
            )
            return
        if not os.path.isdir(self._tex_dir):
            logger.info(
                'Texture dir not found, skipping tex preload.'
            )
            return
        total = self.total
        if tex_futs is None:
            tex_futs = {
                self._tex_executor.submit(
                    self._load_texture, i
                ): i
                for i in range(total)
            }
        logger.info('Collecting %d texture futures...', total)
        t0 = time.perf_counter()
        try:
            with alive_bar(
                total, spinner=None,
                title='PRELOADING TEXTURE FILES...',
                title_length=25, length=15,
                stats=True, elapsed=True,
                manual=False, enrich_print=True,
                force_tty=True
            ) as bar:
                for fut in as_completed(tex_futs):
                    idx = tex_futs[fut]
                    tex = fut.result()
                    with self._lock:
                        self._tex_cache[idx] = tex
                        self._pending_tex.discard(idx)
                    bar()
                bar.title = 'TEXTURE PRELOADING COMPLETE'
                time.sleep(1.0)
        except KeyboardInterrupt:
            logger.warning('Texture preload interrupted.')
            self.cleanup()
            raise
        logger.info(
            'All %d textures preloaded in %.2fs.',
            total, time.perf_counter() - t0,
        )

    def _warm_start(self) -> None:
        t0 = time.perf_counter()
        mesh0 = self._load_mesh(0)
        t_load = time.perf_counter() - t0
        with self._lock:
            self._mesh_cache[0] = mesh0
        t1 = time.perf_counter()
        self._prefetch(0)
        t_prefetch = time.perf_counter() - t1
        logger.debug(
            'Warm start: frame0_load=%.4fs prefetch=%.4fs',
            t_load, t_prefetch,
        )
        logger.info(
            'Warm start: frame 0 loaded, prefetch started.'
        )

    def _get_mesh(self, idx: int) -> pv.PolyData:
        with self._lock:
            if idx in self._mesh_cache:
                return self._mesh_cache[idx]
        try:
            mesh = self._load_mesh(idx)
        except Exception as e:
            logger.error('Mesh load failed [idx=%d]: %s', idx, e)
            mesh = pv.PolyData()
        with self._lock:
            self._mesh_cache[idx] = mesh
        return mesh

    def _ensure_npz_cache(self) -> None:
        os.makedirs(self._npz_dir, exist_ok=True)
        missing = [
            f for f in self._obj_files
            if _is_cache_stale(
                f, _frame_cache_dir(f, self._npz_dir)
            )
        ]
        if not missing:
            return

        workers = WORKER_COUNT
        logger.info(
            'Building frame cache: %d stale/missing (workers=%d)...',
            len(missing), workers,
        )

        total = len(missing)
        chunk_size = max(1, (total + 1) // 2)
        err_count = 0
        try:
            with alive_bar(
                total, spinner=None,
                title='INITIALIZING FRAME CACHE...',
                title_length=25, length=15,
                dual_line=True, stats=True,
                elapsed=True, manual=False,
                enrich_print=False, force_tty=True,
            ) as bar:
                for i in range(0, total, chunk_size):
                    chunk = missing[i: i + chunk_size]
                    with ThreadPoolExecutor(max_workers=workers) as exe:
                        futures = {
                            exe.submit(
                                _dispatch_cache_build, f, self._npz_dir
                            ): f
                            for f in chunk
                        }
                        for fut in as_completed(futures):
                            try:
                                fut.result()
                            except Exception as e:
                                err_count += 1
                                logger.error(
                                    'Cache build error [%s]: %s',
                                    futures[fut], e,
                                )
                            bar()
                    release_process_memory(
                        f'{min(i + chunk_size, total)}/{total}'
                    )

        except KeyboardInterrupt:
            logger.warning('Frame cache build interrupted.')
            self.cleanup()
            raise

        if err_count:
            logger.warning(
                'Frame cache: %d error(s). '
                'Failed frames will be retried during preload.',
                err_count,
            )

        logger.info('Frame cache build completed.')

    def _load_mesh(self, idx: int) -> pv.PolyData:
        obj_path = self._obj_files[idx]
        if self._no_cache:
            mesh = read_polydata(obj_path)
        else:
            frame_dir = _frame_cache_dir(obj_path, self._npz_dir)
            if not os.path.isdir(frame_dir):
                _build_one_subprocess(obj_path, self._npz_dir)
            if os.path.isdir(frame_dir):
                mesh = _load_mesh_frame(frame_dir)
            else:
                raise RuntimeError(
                    f'Cache unavailable: {os.path.basename(obj_path)}'
                )
        if mesh.n_faces_strict > AUTO_DECIMATE_THRESHOLD:
            if mesh.active_texture_coordinates is not None:
                logger.debug(
                    'Auto decimation [idx=%d]: skipped'
                    ' (textured mesh, %d faces)',
                    idx, mesh.n_faces_strict,
                )
            else:
                orig_faces = mesh.n_faces_strict
                ratio = min(
                    AUTO_DECIMATE_MAX_RATIO,
                    orig_faces / AUTO_DECIMATE_MAX_CELLS,
                )
                if not mesh.is_all_triangles:
                    mesh = mesh.triangulate()
                mesh = mesh.decimate(ratio)
                logger.debug(
                    'Auto decimation [idx=%d]: %d -> %d faces'
                    ' (ratio=%.3f)',
                    idx, orig_faces, mesh.n_faces_strict, ratio,
                )
        elif (mesh.n_faces_strict == 0
                and mesh.n_points > (
                    NP_SUBSAMPLE_THRESHOLD
                    if os.path.splitext(obj_path)[1].lower()
                    in (_NPY_EXT, _NPZ_INPUT_EXT)
                    else PT_SUBSAMPLE_THRESHOLD
                )):
            _ss_target = (
                NP_SUBSAMPLE_TARGET
                if os.path.splitext(obj_path)[1].lower()
                in (_NPY_EXT, _NPZ_INPUT_EXT)
                else PT_SUBSAMPLE_TARGET
            )
            orig_pts = mesh.n_points
            step = max(2, orig_pts // _ss_target)
            indices = np.arange(0, orig_pts, step)
            sub = pv.PolyData(mesh.points[indices])
            for key in mesh.point_data.keys():
                arr = mesh.point_data[key]
                if len(arr) == orig_pts:
                    sub.point_data[key] = arr[indices]
            mesh = sub
            logger.debug(
                'Point cloud subsampled [idx=%d]: %d -> %d pts',
                idx, orig_pts, mesh.n_points,
            )
        if self._smooth and 'Normals' not in mesh.point_data:
            mesh.compute_normals(inplace=True)
        if mesh.n_faces_strict == 0:
            if '_rgb_packed' not in mesh.point_data:
                _rgb = pack_pt_colors(mesh)
                if _rgb is not None:
                    mesh.point_data['_rgb_packed'] = _rgb
        return mesh

    def _load_texture(self, idx: int) -> 'pv.Texture | None':
        base = os.path.splitext(
            os.path.basename(self._obj_files[idx])
        )[0]
        for ext in TEX_EXTENSIONS:
            t_path = os.path.join(self._tex_dir, base + ext)
            if os.path.exists(t_path):
                return pv.read_texture(t_path)
        return self._shared_tex

    def _prefetch(self, center_idx: int) -> None:
        fwd = self._preload_ahead
        bwd = max(1, int(fwd * PRELOAD_BACK_RATIO))
        start = max(0, center_idx - bwd)
        end = min(self.total, center_idx + fwd + 1)

        for i in range(start, end):
            self._submit_mesh_prefetch(i)
            self._submit_tex_prefetch(i)

    def _submit_prefetch(
        self, idx: int, cache: dict, pending: set, executor, worker,
    ) -> None:
        with self._lock:
            if idx in cache or idx in pending:
                return
            pending.add(idx)
        executor.submit(worker, idx)

    def _run_prefetch(
        self, idx: int, load_fn, cache: dict, pending: set, label: str,
    ) -> None:
        try:
            item = load_fn(idx)
            with self._lock:
                cache[idx] = item
                pending.discard(idx)
        except OSError as e:
            logger.warning(
                '%s prefetch failed idx=%d: %s', label, idx, e,
            )
            with self._lock:
                pending.discard(idx)

    def _submit_mesh_prefetch(self, idx: int) -> None:
        self._submit_prefetch(
            idx, self._mesh_cache, self._pending_mesh,
            self._mesh_executor, self._prefetch_mesh,
        )

    def _submit_tex_prefetch(self, idx: int) -> None:
        self._submit_prefetch(
            idx, self._tex_cache, self._pending_tex,
            self._tex_executor, self._prefetch_tex,
        )

    def _prefetch_mesh(self, idx: int) -> None:
        self._run_prefetch(
            idx, self._load_mesh,
            self._mesh_cache, self._pending_mesh, 'Mesh',
        )

    def _prefetch_tex(self, idx: int) -> None:
        self._run_prefetch(
            idx, self._load_texture,
            self._tex_cache, self._pending_tex, 'Texture',
        )

    def _evict(self, center_idx: int) -> None:
        if self._preload_all:
            return
        half = self._window_size // 2
        mem_pct = psutil.virtual_memory().percent / 100.0
        if mem_pct > EVICT_MEMORY_THRESHOLD:
            half = max(1, half // 2)
            logger.debug(
                'Memory pressure %.0f%%: evict window halved to %d',
                mem_pct * 100, half,
            )
        lo = center_idx - half
        hi = center_idx + half

        evicted = 0
        with self._lock:
            for cache in (self._mesh_cache, self._tex_cache):
                evict_keys = [k for k in cache if k < lo or k > hi]
                for k in evict_keys:
                    del cache[k]
                evicted += len(evict_keys)

        if evicted:
            now = time.monotonic()
            if now - self._last_evict_release >= _EVICT_RELEASE_INTERVAL:
                self._last_evict_release = now
                release_process_memory('evict')
