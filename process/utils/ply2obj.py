import argparse
import io
import logging
import os
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import numpy as np
import pyvista as pv
from alive_progress import alive_bar

from configs.colorize import Msg
from configs.defaults import WORKER_COUNT

try:
    from PIL import Image
    _HAS_PIL = True
except ImportError:
    _HAS_PIL = False

try:
    from scipy.spatial import Delaunay as _Delaunay
    _HAS_SCIPY = True
except ImportError:
    _HAS_SCIPY = False

MESH_EXTENSIONS = {
    '.ply', '.obj', '.stl', '.off',
    '.gltf', '.glb', '.dae', '.3ds', '.byu',
}
MESH_DIR_ROOT    = Path('input/mesh')
TEXTURE_DIR_ROOT = Path('input/texture')
LOG_DIR          = Path('logs')
LOG_FORMAT       = '%(asctime)s | %(levelname)-8s | %(name)s: %(message)s'
LOG_MSEC_FORMAT  = '%s.%03d'
DEFAULT_WORKERS  = WORKER_COUNT

log = logging.getLogger(__name__)

def _setup_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    handler = logging.FileHandler(
        LOG_DIR / 'ply2obj.log', mode='w', encoding='utf-8'
    )
    handler.setLevel(level)
    fmt = logging.Formatter(LOG_FORMAT)
    fmt.default_msec_format = LOG_MSEC_FORMAT
    handler.setFormatter(fmt)
    logging.basicConfig(level=level, handlers=[handler], force=True)

def _apply_swap_yz(pts: np.ndarray) -> np.ndarray:
    out = pts.copy()
    out[:, 1] = pts[:, 2]
    out[:, 2] = -pts[:, 1]
    return out

def _extract_rgb(mesh: pv.PolyData) -> 'np.ndarray | None':
    rgba = mesh.point_data.get('RGBA')
    if rgba is not None and rgba.ndim == 2 and rgba.shape[1] >= 3:
        return rgba[:, :3].astype(np.uint8)
    r = mesh.point_data.get('red')
    g = mesh.point_data.get('green')
    b = mesh.point_data.get('blue')
    if r is not None and g is not None and b is not None:
        return np.column_stack([r, g, b]).astype(np.uint8)
    return None

def _make_texture_image(rgb: np.ndarray):
    n = len(rgb)
    w = max(1, int(np.ceil(np.sqrt(n))))
    h = int(np.ceil(n / w))
    padded = np.zeros((h * w, 3), dtype=np.uint8)
    padded[:n] = rgb
    return Image.fromarray(padded.reshape(h, w, 3), 'RGB'), w, h

def _make_uv(n: int, w: int, h: int) -> np.ndarray:
    idx = np.arange(n)
    u = (idx % w + 0.5) / w
    v = 1.0 - (idx // w + 0.5) / h
    return np.column_stack([u, v]).astype(np.float32)

def _triangulate_pca(pts: np.ndarray) -> np.ndarray:
    center = pts.mean(axis=0)
    centered = pts - center
    _, _, vh = np.linalg.svd(centered, full_matrices=False)
    pts2d = centered @ vh[:2].T
    tri = _Delaunay(pts2d)
    s = tri.simplices.astype(np.int64)
    faces = np.hstack([np.full((len(s), 1), 3, dtype=np.int64), s])
    return faces.flatten()

def _write_mtl(mtl_path: Path, rel_tex: str) -> None:
    mtl_path.write_text(
        'newmtl material_0\n'
        'Ka 1.0 1.0 1.0\n'
        'Kd 1.0 1.0 1.0\n'
        'Ks 0.0 0.0 0.0\n'
        f'map_Kd {rel_tex}\n',
        encoding='utf-8',
    )

def _write_obj(
    obj_path: Path,
    pts: np.ndarray,
    faces_flat: 'np.ndarray | None',
    uv: 'np.ndarray | None',
    mtl_name: 'str | None',
) -> None:
    buf = io.StringIO()
    if mtl_name:
        buf.write(f'mtllib {mtl_name}\n')

    np.savetxt(buf, pts, fmt='v %.6f %.6f %.6f')

    if uv is not None:
        np.savetxt(buf, uv, fmt='vt %.6f %.6f')

    if mtl_name:
        buf.write('usemtl material_0\n')

    if faces_flat is not None and len(faces_flat) > 0:
        n_per = int(faces_flat[0])
        tris = (faces_flat.reshape(-1, n_per + 1)[:, 1:] + 1).astype(
            np.int64
        )
        if uv is not None:

            data = np.column_stack(
                [tris[:, 0], tris[:, 0],
                 tris[:, 1], tris[:, 1],
                 tris[:, 2], tris[:, 2]]
            )
            np.savetxt(buf, data, fmt='f %d/%d %d/%d %d/%d')
        else:
            np.savetxt(buf, tris, fmt='f %d %d %d')

    obj_path.write_text(buf.getvalue(), encoding='utf-8')

def _get_native_faces(mesh: pv.PolyData) -> 'np.ndarray | None':
    if mesh.n_faces_strict == 0:
        return None
    if not mesh.is_all_triangles:
        mesh = mesh.triangulate()
    return mesh.faces

def _build_pc_assets(
    pts: np.ndarray,
    rgb: 'np.ndarray | None',
    tex_dir: 'Path | None',
    name: str,
) -> tuple:
    uv = None
    faces = None
    mtl_name = None
    tex_path = None

    if rgb is not None and _HAS_PIL and tex_dir is not None:
        tex_dir.mkdir(parents=True, exist_ok=True)
        img, tw, th = _make_texture_image(rgb)
        tex_path = tex_dir / f'{name}.png'
        img.save(str(tex_path))
        uv = _make_uv(len(pts), tw, th)

    if _HAS_SCIPY:
        faces = _triangulate_pca(pts)

    if uv is not None:
        mtl_name = f'{name}.mtl'

    return faces, uv, mtl_name, tex_path

def _convert_worker(args: tuple) -> tuple:
    (
        ply_str, obj_str, swap_yz, is_pc,
        shared_faces, shared_uv, shared_mtl, first_n_points,
    ) = args

    ply_path = Path(ply_str)
    out_obj  = Path(obj_str)

    try:
        mesh = pv.read(ply_str)
        pts  = mesh.points.astype(np.float64)
        if swap_yz:
            pts = _apply_swap_yz(pts)

        if is_pc:
            if (shared_faces is not None
                    and mesh.n_points == first_n_points):
                faces, uv, mtl = shared_faces, shared_uv, shared_mtl
            else:

                faces = _triangulate_pca(pts) if _HAS_SCIPY else None
                uv    = None
                mtl   = None
                msg = (
                    f'Point count mismatch {ply_path.name}'
                    f' ({mesh.n_points} vs {first_n_points}),'
                    f' re-triangulated without texture'
                )
                return False, ply_path.name, msg
        else:
            faces = _get_native_faces(mesh)
            uv    = None
            mtl   = None

        out_obj.parent.mkdir(parents=True, exist_ok=True)
        _write_obj(out_obj, pts, faces, uv, mtl)
        return True, ply_path.name, str(out_obj)

    except Exception as e:
        return False, ply_path.name, str(e)

def convert_single(input_path: Path, swap_yz: bool) -> None:
    stem     = input_path.stem
    out_name = f'input_{stem}'
    out_dir  = MESH_DIR_ROOT / out_name
    out_obj  = out_dir / f'{stem}.obj'
    tex_dir  = TEXTURE_DIR_ROOT / out_name

    try:
        mesh = pv.read(str(input_path))
    except Exception as e:
        log.error('Cannot read %s: %s', input_path.name, e)
        return

    pts = mesh.points.astype(np.float64)
    if swap_yz:
        pts = _apply_swap_yz(pts)

    is_pc = mesh.n_faces_strict == 0
    out_dir.mkdir(parents=True, exist_ok=True)

    if is_pc:
        rgb = _extract_rgb(mesh)
        faces, uv, mtl_name, tex_path = _build_pc_assets(
            pts, rgb, tex_dir, out_name
        )
        if mtl_name and tex_path:
            rel_tex = os.path.relpath(tex_path, out_obj.parent)
            _write_mtl(out_dir / mtl_name, rel_tex)
        _write_obj(out_obj, pts, faces, uv, mtl_name)
        log.info('Point cloud OK: %d pts → %s', len(pts), out_obj)
    else:
        _write_obj(out_obj, pts, _get_native_faces(mesh), None, None)
        log.info('Mesh OK: %s', out_obj)

    print(f'Output: {out_obj}')
    print(f'Run   : python meshViewer.py -i {out_name}')

def convert_directory(
    input_dir: Path, swap_yz: bool, n_workers: int
) -> None:
    files = sorted(
        f for f in input_dir.iterdir()
        if f.suffix.lower() in MESH_EXTENSIONS
    )
    if not files:
        log.error('No mesh files found in: %s', input_dir)
        return

    out_name = f'{input_dir.name}_obj'
    out_dir  = MESH_DIR_ROOT / out_name
    tex_dir  = TEXTURE_DIR_ROOT / out_name
    out_dir.mkdir(parents=True, exist_ok=True)

    first_mesh    = pv.read(str(files[0]))
    is_pc         = first_mesh.n_faces_strict == 0
    first_n_pts   = first_mesh.n_points
    shared_faces  = None
    shared_uv     = None
    shared_mtl    = None

    if is_pc:
        pts0 = first_mesh.points.astype(np.float64)
        if swap_yz:
            pts0 = _apply_swap_yz(pts0)
        rgb0 = _extract_rgb(first_mesh)
        shared_faces, shared_uv, shared_mtl, tex_path = _build_pc_assets(
            pts0, rgb0, tex_dir, out_name
        )
        if shared_mtl and tex_path:
            rel_tex = os.path.relpath(tex_path, out_dir)
            _write_mtl(out_dir / shared_mtl, rel_tex)
        log.info(
            'Shared texture: %s, triangles: %d',
            tex_path,
            (len(shared_faces) // 4) if shared_faces is not None else 0,
        )

    log.info(
        'Converting %d files → %s  workers=%d  is_pc=%s',
        len(files), out_dir, n_workers, is_pc,
    )

    worker_args = [
        (
            str(f),
            str(out_dir / f'{f.stem}.obj'),
            swap_yz, is_pc,
            shared_faces, shared_uv, shared_mtl, first_n_pts,
        )
        for f in files
    ]

    ok = err = 0

    with ProcessPoolExecutor(max_workers=n_workers) as executor:
        futures = {
            executor.submit(_convert_worker, a): a[0]
            for a in worker_args
        }
        with alive_bar(
            len(files), spinner=None, title='PROCESSING…',
            title_length=25, length=15, dual_line=True,
            stats=True, elapsed=True, force_tty=True,
        ) as bar:
            for future in as_completed(futures):
                success, name, detail = future.result()
                if success:
                    ok += 1
                    bar.text = Msg.Dim(
                        f'RESULT: "{detail}"', verbose=True
                    )
                else:
                    err += 1
                    log.error('FAIL %s — %s', name, detail)
                bar()
            bar.title = 'FILE CONVERTING COMPLETE'

    log.info('Done: %d converted, %d failed', ok, err)
    print(f'Output dir: {out_dir}')
    print(f'Run       : python meshViewer.py -i {out_name}')

def convert(input_path: str, swap_yz: bool, n_workers: int) -> None:
    p = Path(input_path)
    if p.is_file():
        convert_single(p, swap_yz)
    elif p.is_dir():
        convert_directory(p, swap_yz, n_workers)
    else:
        log.error('Input not found: %s', input_path)

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description='PLY → OBJ 변환 (포인트 클라우드: 텍스처 아틀라스 포함)'
    )
    parser.add_argument(
        '-i', '--input', required=True,
        help='단일 PLY 파일 또는 PLY 시퀀스 디렉토리',
    )
    parser.add_argument(
        '--keep-axis', action='store_true', default=False,
        help='Y-Z 축 스왑 없이 원본 좌표 유지',
    )
    parser.add_argument(
        '-j', '--workers', type=int, default=DEFAULT_WORKERS,
        metavar='N',
        help=f'병렬 워커 수 (기본값: {DEFAULT_WORKERS})',
    )
    parser.add_argument(
        '-v', '--verbose', action='store_true',
        help='DEBUG 레벨 로그 출력',
    )
    return parser.parse_args()

def main() -> None:
    args = parse_args()
    _setup_logging(args.verbose)
    if not _HAS_PIL:
        log.warning('Pillow not installed — texture output disabled')
    if not _HAS_SCIPY:
        log.warning(
            'scipy not installed — point cloud triangulation disabled'
        )
    convert(
        args.input,
        swap_yz=not args.keep_axis,
        n_workers=args.workers,
    )

if __name__ == '__main__':
    main()
