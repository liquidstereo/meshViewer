import gc
import os
import time
import hashlib
import logging
import threading
from concurrent.futures import (
    ThreadPoolExecutor, ProcessPoolExecutor, as_completed,
)

import numpy as np
import pyvista as pv
from alive_progress import alive_bar

import psutil

from configs.defaults import (
    DEFAULT_PRELOAD_ALL,
    DEFAULT_WINDOW_SIZE, DEFAULT_PRELOAD_AHEAD,
    PRELOAD_BACK_RATIO, EVICT_MEMORY_THRESHOLD,
    DEFAULT_MESH_WORKERS, DEFAULT_TEX_WORKERS,
    CACHE_DIR_ROOT, TEX_EXTENSIONS,
    TEXTURE_DIR_ROOT,
    AUTO_DECIMATE_THRESHOLD, AUTO_DECIMATE_MAX_CELLS, AUTO_DECIMATE_MAX_RATIO,
    PT_SUBSAMPLE_THRESHOLD, PT_SUBSAMPLE_TARGET,
)
from configs.colorize import Msg
from process.utils.extract_texture import extract_embedded_texture

logger = logging.getLogger(__name__)

_UV_CANDIDATE_NAMES = (
    'TEXCOORD_0', 'TEXCOORD_1',
    'TextureCoordinates', 'Texture Coordinates', 'UV',
)

_GLTF_EXTS = {'.glb', '.gltf'}

def _frame_cache_dir(obj_path, npz_dir):
    name = os.path.basename(obj_path)
    base, ext = os.path.splitext(name)
    return os.path.join(npz_dir, f'{base}_{ext[1:]}')

def _is_cache_stale(src_path: str, frame_dir: str) -> bool:
    sentinel = os.path.join(frame_dir, 'points.npy')
    if not os.path.exists(sentinel):
        return True
    return os.path.getmtime(src_path) > os.path.getmtime(sentinel)

def _fix_gltf_v_flip(mesh: 'pv.PolyData') -> None:
    tc = mesh.active_texture_coordinates
    if tc is None:
        return
    fixed = tc.copy()
    fixed[:, 1] = 1.0 - fixed[:, 1]
    mesh.active_texture_coordinates = fixed
    logger.info('glTF UV V coordinate restored (1 - V).')

def _activate_texture_coords(mesh: 'pv.PolyData') -> None:
    if mesh.active_texture_coordinates is not None:
        logger.debug('UV already active: skipping activation.')
        return
    pd = mesh.GetPointData()
    for name in _UV_CANDIDATE_NAMES:
        arr = pd.GetArray(name)
        if arr is None:
            continue
        if arr.GetNumberOfComponents() < 2:
            continue
        pd.SetActiveTCoords(name)
        logger.info('Texture coordinates activated: "%s"', name)
        return
    logger.debug('No UV array found in point_data.')

def _read_as_polydata(path: str) -> 'pv.PolyData':
    result = pv.read(path)
    is_gltf = os.path.splitext(path)[1].lower() in _GLTF_EXTS
    if not isinstance(result, pv.MultiBlock):
        if not isinstance(result, pv.PolyData):
            result = result.extract_surface()
        _activate_texture_coords(result)
        if is_gltf:
            _fix_gltf_v_flip(result)
        return result
    combined = result.combine()
    if isinstance(combined, pv.PolyData):
        poly = combined
    else:
        poly = combined.extract_surface(
            algorithm='dataset_surface'
        )
    _activate_texture_coords(poly)
    if is_gltf:
        _fix_gltf_v_flip(poly)
    return poly

def _build_single_npz(obj_path, npz_dir):
    _log = logging.getLogger(__name__)
    try:
        mesh = _read_as_polydata(obj_path)
        frame_dir = _frame_cache_dir(obj_path, npz_dir)
        os.makedirs(frame_dir, exist_ok=True)
        if mesh.faces.size > 0:
            faces = mesh.faces
            if int(faces.max()) < np.iinfo(np.int32).max:
                faces = faces.astype(np.int32)
            np.save(os.path.join(frame_dir, 'faces.npy'), faces)
        for key in mesh.point_data.keys():
            np.save(
                os.path.join(frame_dir, f'pd_{key}.npy'),
                mesh.point_data[key],
            )
        tc = mesh.active_texture_coordinates
        if tc is not None:
            np.save(os.path.join(frame_dir, 'tcoords.npy'), tc)
        np.save(os.path.join(frame_dir, 'points.npy'), mesh.points)
    except Exception as e:
        _log.error('Frame cache build failed [%s]: %s', obj_path, e)
        raise

def _load_mesh_frame(frame_dir: str) -> 'pv.PolyData':
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

def _pack_pt_colors(mesh) -> 'np.ndarray | None':
    rgba = mesh.point_data.get('RGBA')
    if rgba is not None and rgba.ndim == 2 and rgba.shape[1] >= 3:
        return np.ascontiguousarray(rgba[:, :3], dtype=np.uint8)
    rgb = mesh.point_data.get('RGB')
    if rgb is not None and rgb.ndim == 2 and rgb.shape[1] >= 3:
        return np.ascontiguousarray(rgb[:, :3], dtype=np.uint8)
    c0 = mesh.point_data.get('COLOR_0')
    if c0 is not None and c0.ndim == 2 and c0.shape[1] >= 3:
        return np.ascontiguousarray(
            (c0[:, :3] * 255).clip(0, 255), dtype=np.uint8
        )
    r = mesh.point_data.get('red')
    g = mesh.point_data.get('green')
    b = mesh.point_data.get('blue')
    if r is not None and g is not None and b is not None:
        return np.ascontiguousarray(
            np.column_stack([r, g, b]), dtype=np.uint8
        )
    return None

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
        self._mesh_executor = ThreadPoolExecutor(
            max_workers=DEFAULT_MESH_WORKERS
        )
        self._tex_executor = ThreadPoolExecutor(
            max_workers=DEFAULT_TEX_WORKERS
        )
        self._pending_mesh = set()
        self._pending_tex = set()

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
        self._shared_tex = self._find_shared_texture()
        tex_needed = self._shared_tex is None
        npz_needed = not self._no_cache

        if tex_needed and npz_needed:

            logger.info('Starting parallel: texture extraction + NPZ build.')
            with ThreadPoolExecutor(max_workers=2) as exe:
                tex_fut = exe.submit(
                    extract_embedded_texture,
                    obj_files[0], self._tex_dir, self._input_name,
                )
                npz_fut = exe.submit(self._ensure_npz_cache)
                extracted = tex_fut.result()
                npz_fut.result()
            if extracted is not None:
                self._shared_tex = pv.read_texture(extracted)
                logger.info(
                    'Texture loaded from extracted file: %s', extracted,
                )
        else:
            if tex_needed:
                extracted = extract_embedded_texture(
                    obj_files[0], self._tex_dir, self._input_name,
                )
                if extracted is not None:
                    self._shared_tex = pv.read_texture(extracted)
                    logger.info(
                        'Texture loaded from extracted file: %s', extracted,
                    )
            if npz_needed:
                self._ensure_npz_cache()
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
        gc.collect()
        logger.info('FrameBuffer cleanup COMPLETE')

    def _preload_all_meshes(self) -> None:
        total = self.total
        logger.info('Preloading all %d meshes...', total)
        t0 = time.perf_counter()
        try:
            with alive_bar(
                total, spinner=None,
                title='PRELOADING MESH FILES…',
                title_length=25, length=15,
                stats=True, elapsed=True,
                manual=False, enrich_print=True,
                force_tty=True
            ) as bar:
                futs = {
                    self._mesh_executor.submit(
                        self._load_mesh, i
                    ): i
                    for i in range(total)
                }
                for fut in as_completed(futs):
                    idx = futs[fut]
                    mesh = fut.result()
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
        self._max_points = 0
        with self._lock:
            vals = list(self._mesh_cache.values())
        if vals and all(m.n_faces_strict == 0 for m in vals):
            self._max_points = max(m.n_points for m in vals)
            logger.debug('PT max_points: %d', self._max_points)

    def _find_shared_texture(self):
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

        tex = pv.read_texture(t_path)
        logger.info('Shared texture found: %s', t_path)
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
        if not os.path.isdir(self._tex_dir):
            logger.info(
                'Texture dir not found, skipping tex preload.'
            )
            return
        if self._shared_tex is not None:
            with self._lock:
                for i in range(self.total):
                    self._tex_cache[i] = self._shared_tex
            logger.info(
                'Shared texture applied to all %d frames.',
                self.total,
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
                title='PRELOADING TEXTURE FILES…',
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

    def _get_mesh(self, idx):
        with self._lock:
            if idx in self._mesh_cache:
                return self._mesh_cache[idx]
        mesh = self._load_mesh(idx)
        with self._lock:
            self._mesh_cache[idx] = mesh
        return mesh

    def _ensure_npz_cache(self):
        os.makedirs(self._npz_dir, exist_ok=True)
        missing = [
            f for f in self._obj_files
            if _is_cache_stale(
                f, _frame_cache_dir(f, self._npz_dir)
            )
        ]
        if not missing:
            return

        workers = DEFAULT_MESH_WORKERS
        logger.info(
            'Building frame cache: %d stale/missing (workers=%d)...',
            len(missing), workers,
        )
        try:
            with alive_bar(
                len(missing), spinner=None,
                title='INITIALIZING NPZ CACHE…',
                title_length=25, length=15,
                dual_line=True, stats=True,
                elapsed=True, manual=False,
                enrich_print=True, force_tty=True
            ) as bar:
                with ProcessPoolExecutor(
                    max_workers=workers
                ) as exe:
                    futs = {
                        exe.submit(
                            _build_single_npz,
                            f, self._npz_dir
                        ): f
                        for f in missing
                    }
                    for fut in as_completed(futs):
                        src = futs[fut]
                        try:
                            fut.result()
                        except Exception as e:
                            logger.error(
                                'Frame cache error [%s]: %s', src, e
                            )
                            raise
                        bar()
                bar.title = 'NPZ FILE CACHING COMPLETE'
        except KeyboardInterrupt:
            logger.warning('Frame cache build interrupted.')
            self.cleanup()
            raise

    def _load_mesh(self, idx):
        obj_path = self._obj_files[idx]
        if self._no_cache:
            mesh = _read_as_polydata(obj_path)
        else:
            frame_dir = _frame_cache_dir(obj_path, self._npz_dir)
            mesh = (
                _load_mesh_frame(frame_dir)
                if os.path.isdir(frame_dir)
                else _read_as_polydata(obj_path)
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
                and mesh.n_points > PT_SUBSAMPLE_THRESHOLD):
            orig_pts = mesh.n_points
            step = max(2, orig_pts // PT_SUBSAMPLE_TARGET)
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
            _rgb = _pack_pt_colors(mesh)
            if _rgb is not None:
                mesh.point_data['_rgb_packed'] = _rgb
        return mesh

    def _load_texture(self, idx):
        base = os.path.splitext(
            os.path.basename(self._obj_files[idx])
        )[0]
        for ext in TEX_EXTENSIONS:
            t_path = os.path.join(self._tex_dir, base + ext)
            if os.path.exists(t_path):
                return pv.read_texture(t_path)
        return self._shared_tex

    def _prefetch(self, center_idx):
        fwd = self._preload_ahead
        bwd = max(1, int(fwd * PRELOAD_BACK_RATIO))
        start = max(0, center_idx - bwd)
        end = min(self.total, center_idx + fwd + 1)

        for i in range(start, end):
            self._submit_mesh_prefetch(i)
            self._submit_tex_prefetch(i)

    def _submit_prefetch(self, idx, cache, pending, executor, worker):
        with self._lock:
            if idx in cache or idx in pending:
                return
            pending.add(idx)
        executor.submit(worker, idx)

    def _run_prefetch(self, idx, load_fn, cache, pending, label):
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

    def _submit_mesh_prefetch(self, idx):
        self._submit_prefetch(
            idx, self._mesh_cache, self._pending_mesh,
            self._mesh_executor, self._prefetch_mesh,
        )

    def _submit_tex_prefetch(self, idx):
        self._submit_prefetch(
            idx, self._tex_cache, self._pending_tex,
            self._tex_executor, self._prefetch_tex,
        )

    def _prefetch_mesh(self, idx):
        self._run_prefetch(
            idx, self._load_mesh,
            self._mesh_cache, self._pending_mesh, 'Mesh',
        )

    def _prefetch_tex(self, idx):
        self._run_prefetch(
            idx, self._load_texture,
            self._tex_cache, self._pending_tex, 'Texture',
        )

    def _evict(self, center_idx):
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

        with self._lock:
            for cache in (
                self._mesh_cache, self._tex_cache
            ):
                evict_keys = [
                    k for k in cache
                    if k < lo or k > hi
                ]
                for k in evict_keys:
                    del cache[k]

def load_audio_data(
    audio_path: str,
    start: float,
    end: float | None,
    fps: int,
) -> tuple:
    from process.audio.pipeline import (
        prepare_audio_data, PREPARE_AUDIO_STEPS,
    )
    base_name = os.path.splitext(os.path.basename(audio_path))[0]
    with alive_bar(
                PREPARE_AUDIO_STEPS, spinner=None,
                title='PROCESSING AUDIO DATA…',
                title_length=25, length=15,
                dual_line=True, stats=True,
                elapsed=True, manual=False,
                enrich_print=False, force_tty=True
            ) as bar:
        result = prepare_audio_data(audio_path, start, end, fps, bar=bar)
        bar.title = 'AUDIO PROCESSING COMPLETE'
    return result
