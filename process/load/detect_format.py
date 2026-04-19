import logging
from pathlib import Path

log = logging.getLogger(__name__)

_PLY_EXT  = '.ply'
_MESH_GEO = 'mesh'
_PC_GEO   = 'point_cloud'

_MESH_ONLY_EXTS = frozenset({
    '.obj', '.stl', '.vtp', '.vtk',
    '.off', '.glb', '.gltf',
    '.dae', '.3ds', '.byu',
})

def _detect_ply(path: Path) -> str:
    face_count = 0
    try:
        with open(path, 'rb') as f:
            for raw in f:
                line = raw.decode('ascii', errors='ignore').strip()
                if line == 'end_header':
                    break
                if line.startswith('element face'):
                    try:
                        face_count = int(line.split()[-1])
                    except (ValueError, IndexError):
                        pass
    except OSError as e:
        log.warning('PLY header read failed (%s): %s', path.name, e)
        return _MESH_GEO
    result = _PC_GEO if face_count == 0 else _MESH_GEO
    log.debug(
        'PLY header: element face=%d -> %s', face_count, result
    )
    return result

def _detect_trimesh(path: Path) -> str:
    try:
        import trimesh
        loaded = trimesh.load(str(path), process=False, force=None)
        if isinstance(loaded, trimesh.PointCloud):
            log.debug('trimesh: PointCloud -> %s', path.name)
            return _PC_GEO
        log.debug('trimesh: Mesh -> %s', path.name)
        return _MESH_GEO
    except Exception as e:
        log.warning(
            'trimesh detection failed (%s): %s — assuming mesh',
            path.name, e,
        )
        return _MESH_GEO

def detect_geometry_type(path: 'str | Path') -> str:
    p = Path(path)
    ext = p.suffix.lower()
    if ext == _PLY_EXT:
        return _detect_ply(p)
    if ext in _MESH_ONLY_EXTS:
        log.debug('extension-based: %s -> mesh', p.name)
        return _MESH_GEO
    return _detect_trimesh(p)
