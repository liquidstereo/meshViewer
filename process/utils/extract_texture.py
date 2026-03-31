import os
import logging

logger = logging.getLogger(__name__)

_SUPPORTED_EXTS = {'.glb', '.gltf', '.obj', '.ply', '.fbx', '.dae'}

def _image_from_geometry(geo):
    visual = getattr(geo, 'visual', None)
    if visual is None:
        return None
    mat = getattr(visual, 'material', None)
    if mat is None:
        return None
    for attr in ('baseColorTexture', 'image'):
        img = getattr(mat, attr, None)
        if img is not None:
            return img
    return None

def _image_from_scene(scene) -> object:
    for name, geo in scene.geometry.items():
        img = _image_from_geometry(geo)
        if img is not None:
            logger.debug(
                'Texture image found in geometry: %s', name
            )
            return img
    return None

def extract_embedded_texture(
    mesh_path: str,
    tex_dir: str,
    stem: str,
) -> str | None:
    ext = os.path.splitext(mesh_path)[1].lower()
    if ext not in _SUPPORTED_EXTS:
        logger.debug(
            'Texture extraction skipped: unsupported ext "%s" (%s)',
            ext, mesh_path,
        )
        return None

    out_path = os.path.join(tex_dir, stem + '.png')
    if os.path.exists(out_path):
        logger.info(
            'Embedded texture already extracted: %s', out_path
        )
        return out_path

    try:
        import trimesh
    except ImportError:
        logger.warning(
            'trimesh is not installed; skipping texture extraction.'
        )
        return None

    logger.info(
        'Scanning embedded texture: %s', mesh_path
    )
    try:
        data = trimesh.load(mesh_path, force='scene')
    except Exception as exc:
        logger.warning(
            'trimesh failed to load "%s": %s', mesh_path, exc
        )
        return None

    img = _image_from_scene(data)
    if img is None:
        logger.info(
            'No embedded texture image found in: %s', mesh_path
        )
        return None

    _MIN_TEX_SIZE = 16
    if img.width < _MIN_TEX_SIZE or img.height < _MIN_TEX_SIZE:
        logger.info(
            'Extracted texture too small (%dx%d), skipping: %s',
            img.width, img.height, mesh_path,
        )
        return None

    os.makedirs(tex_dir, exist_ok=True)
    try:
        img.save(out_path)
    except Exception as exc:
        logger.warning(
            'Failed to save extracted texture to "%s": %s',
            out_path, exc,
        )
        return None

    logger.info('Embedded texture extracted -> %s', out_path)
    return out_path
