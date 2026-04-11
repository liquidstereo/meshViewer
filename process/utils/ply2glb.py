import argparse
import logging
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from configs.colorize import Msg

import numpy as np
import trimesh
from alive_progress import alive_bar

from configs.defaults import WORKER_COUNT

MESH_EXTENSIONS = {
    '.ply', '.obj', '.stl', '.off',
    '.gltf', '.glb', '.dae', '.3ds', '.byu'
}
TEXTURE_EXTS = ('.png', '.jpg', '.jpeg', '.webp', '.bmp', '.tga')
MESH_DIR_ROOT = Path('input/mesh')
DEFAULT_WORKERS = WORKER_COUNT

log = logging.getLogger(__name__)

LOG_DIR = Path('logs')
LOG_FORMAT = '%(asctime)s | %(levelname)-8s | %(name)s: %(message)s'
LOG_MSEC_FORMAT = '%s.%03d'

def _setup_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_path = LOG_DIR / 'ply2glb.log'
    handler = logging.FileHandler(log_path, mode='w', encoding='utf-8')
    handler.setLevel(level)
    formatter = logging.Formatter(LOG_FORMAT)
    formatter.default_msec_format = LOG_MSEC_FORMAT
    handler.setFormatter(formatter)
    logging.basicConfig(level=level, handlers=[handler], force=True)

def _find_texture(mesh_path: Path) -> Path | None:
    stem = mesh_path.stem
    search_dirs = [
        mesh_path.parent,
        mesh_path.parent / 'texture',
        mesh_path.parent.parent / 'texture' / stem,
    ]
    for d in search_dirs:
        for ext in TEXTURE_EXTS:
            cand = d / f'{stem}{ext}'
            if cand.exists():
                return cand
    return None

def _load_mesh(mesh_path: Path) -> trimesh.Trimesh:
    loaded = trimesh.load(str(mesh_path), process=False)
    if isinstance(loaded, trimesh.Scene):
        parts = list(loaded.geometry.values())
        loaded = trimesh.util.concatenate(parts)
    return loaded

def _swap_yz(mesh: trimesh.Trimesh) -> trimesh.Trimesh:
    verts = np.array(mesh.vertices)
    x = verts[:, 0]
    y = verts[:, 2].copy()
    z = -verts[:, 1]
    verts[:, 0] = x
    verts[:, 1] = y
    verts[:, 2] = z
    mesh.vertices = verts
    return mesh

def _attach_texture_if_needed(
    mesh: trimesh.Trimesh,
    mesh_path: Path
) -> trimesh.Trimesh:
    if getattr(mesh.visual, 'kind', None) != 'texture':
        return mesh

    mat = mesh.visual.material
    has_img = (
        (hasattr(mat, 'image') and mat.image is not None)
        or (
            hasattr(mat, 'baseColorTexture')
            and mat.baseColorTexture is not None
        )
    )
    if has_img:
        log.debug('Texture already embedded: %s', mesh_path.name)
        return mesh

    tex_path = _find_texture(mesh_path)
    if tex_path is None:
        log.debug('No texture file found for: %s', mesh_path.name)
        return mesh

    from PIL import Image
    img = Image.open(tex_path)
    material = trimesh.visual.material.PBRMaterial(
        baseColorTexture=img
    )
    mesh.visual = trimesh.visual.TextureVisuals(
        uv=mesh.visual.uv,
        material=material
    )
    log.debug('Texture attached: %s → %s', mesh_path.name, tex_path.name)
    return mesh

def _describe_visual(mesh: trimesh.Trimesh) -> str:
    kind = getattr(mesh.visual, 'kind', None)
    if kind == 'texture':
        mat = mesh.visual.material
        has_img = (
            (hasattr(mat, 'image') and mat.image is not None)
            or (
                hasattr(mat, 'baseColorTexture')
                and mat.baseColorTexture is not None
            )
        )
        return 'texture+image' if has_img else 'uv-only'
    if kind in ('vertex', 'face'):
        vc = mesh.visual.vertex_colors
        if vc is not None and len(vc) > 0:
            return 'vertex-color'
    return 'no-color'

def convert_file(
    mesh_path: Path,
    out_path: Path,
    swap_yz: bool,
) -> bool:
    try:
        mesh = _load_mesh(mesh_path)
        if swap_yz:
            mesh = _swap_yz(mesh)
        mesh = _attach_texture_if_needed(mesh, mesh_path)
        visual_desc = _describe_visual(mesh)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        mesh.export(str(out_path), file_type='glb')
        log.info(
            'OK [%s] %s → %s',
            visual_desc,
            mesh_path.name,
            out_path
        )
        return True
    except Exception as e:
        log.error('FAIL %s — %s', mesh_path.name, e)
        return False

def _convert_worker(args: tuple) -> tuple:
    mesh_str, out_str, swap_yz = args
    mesh_path = Path(mesh_str)
    out_path = Path(out_str)
    success = convert_file(mesh_path, out_path, swap_yz)
    return success, mesh_path.name, out_str

def convert_single(input_path: Path, swap_yz: bool) -> None:
    out_path = MESH_DIR_ROOT / f'input_{input_path.stem}.glb'
    convert_file(input_path, out_path, swap_yz)

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

    out_dir = MESH_DIR_ROOT / f'{input_dir.name}_glb'
    log.info(
        'Converting %d files → %s  workers=%d',
        len(files), out_dir, n_workers,
    )

    worker_args = [
        (str(f), str(out_dir / f'{f.stem}.glb'), swap_yz)
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
                bar()
            bar.title = 'FILE CONVERTING COMPLETE'

    log.info('Done: %d converted, %d failed', ok, err)

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
        description='Mesh → GLB 변환 (텍스처·버텍스컬러 보존)'
    )
    parser.add_argument(
        '-i', '--input',
        required=True,
        help='단일 파일 또는 디렉토리 경로'
    )
    parser.add_argument(
        '--keep-axis',
        action='store_true',
        default=False,
        help='Y-Z 축 스왑 없이 원본 좌표 유지 (소스가 이미 Y-up인 경우)'
    )
    parser.add_argument(
        '-j', '--workers', type=int, default=DEFAULT_WORKERS,
        metavar='N',
        help=f'병렬 워커 수 (기본값: {DEFAULT_WORKERS})',
    )
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='DEBUG 레벨 로그 출력'
    )
    return parser.parse_args()

def main() -> None:
    args = parse_args()
    _setup_logging(args.verbose)
    convert(
        args.input,
        swap_yz=not args.keep_axis,
        n_workers=args.workers,
    )

if __name__ == '__main__':
    main()
