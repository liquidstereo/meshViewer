import os
import logging

import numpy as np
import pyvista as pv

from process.load.memory_guard import evict_file_cache

logger = logging.getLogger(__name__)

GS_CACHE_FILE = 'gs_cache.npz'

def is_gs_ply(obj_path: str) -> bool:
    if os.path.splitext(obj_path)[1].lower() != '.ply':
        return False
    try:
        with open(obj_path, 'rb') as f:
            header = f.read(4096)
        return b'f_dc_0' in header
    except OSError:
        return False

def build_gs_npz_cache(obj_path: str, frame_dir: str) -> None:
    from plyfile import PlyData
    try:
        os.makedirs(frame_dir, exist_ok=True)

        ply = PlyData.read(obj_path)
        v = ply['vertex'].data

        xyz = np.column_stack(
            [v['x'], v['y'], v['z']]
        ).astype(np.float32)

        fields = set(v.dtype.names)

        features = np.column_stack(
            [v['f_dc_0'], v['f_dc_1'], v['f_dc_2']]
        ).astype(np.float32) if 'f_dc_0' in fields else np.empty(
            (len(xyz), 0), dtype=np.float32
        )

        opacity = v['opacity'].astype(np.float32).reshape(-1)\
            if 'opacity' in fields\
            else np.empty(len(xyz), dtype=np.float32)

        scale = np.column_stack(
            [v['scale_0'], v['scale_1'], v['scale_2']]
        ).astype(np.float32) if 'scale_0' in fields else np.empty(
            (len(xyz), 0), dtype=np.float32
        )

        rotation = np.column_stack(
            [v['rot_0'], v['rot_1'], v['rot_2'], v['rot_3']]
        ).astype(np.float32) if 'rot_0' in fields else np.empty(
            (len(xyz), 0), dtype=np.float32
        )

        sh_keys = sorted(n for n in fields if n.startswith('f_rest_'))
        sh = np.stack(
            [v[k] for k in sh_keys], axis=1
        ).astype(np.float32) if sh_keys else np.empty(
            (len(xyz), 0), dtype=np.float32
        )

        has_rgb = 'red' in fields and 'green' in fields and 'blue' in fields
        color = np.column_stack(
            [v['red'], v['green'], v['blue']]
        ).astype(np.uint8) if has_rgb else np.empty(
            (len(xyz), 0), dtype=np.uint8
        )

        cache_path = os.path.join(frame_dir, GS_CACHE_FILE)
        np.savez(
            cache_path,
            xyz=xyz,
            features=features,
            opacity=opacity,
            scale=scale,
            rotation=rotation,
            sh=sh,
            color=color,
        )
        evict_file_cache(cache_path)
    except Exception as e:
        logger.error('GS cache build failed [%s]: %s', obj_path, e)
        raise

def load_gs_frame(frame_dir: str) -> pv.PolyData:
    data = np.load(os.path.join(frame_dir, GS_CACHE_FILE))
    mesh = pv.PolyData(data['xyz'])
    color = data['color']
    if color.shape[1] >= 3:
        mesh.point_data['_rgb_packed'] = np.ascontiguousarray(
            color[:, :3], dtype=np.uint8
        )
    return mesh

def pack_pt_colors(mesh: pv.PolyData) -> 'np.ndarray | None':
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
