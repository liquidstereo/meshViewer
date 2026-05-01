import os
import logging

import numpy as np
import pyvista as pv

from configs.settings import (
    NPY_AS_POINTCLOUD,
    DATA_NORMALIZE, DATA_NORMALIZE_VALUE,
    DATA_NORMALIZE_AXIS, DATA_NORMALIZE_LOG,
)

logger = logging.getLogger(__name__)

def _normalize_pts(pts: np.ndarray) -> np.ndarray:
    if not DATA_NORMALIZE or DATA_NORMALIZE_VALUE <= 0.0:
        return pts
    if DATA_NORMALIZE_LOG and pts.shape[1] >= 3:
        pts = pts.copy()
        pts[:, 2] = np.log1p(np.maximum(pts[:, 2], 0.0))
    p_min = pts.min(axis=0)
    p_max = pts.max(axis=0)
    center = (p_min + p_max) * 0.5
    if DATA_NORMALIZE_AXIS == 'per_axis':
        extent = p_max - p_min
        extent = np.where(extent < 1e-8, 1.0, extent)
        return (
            (pts - center) * (DATA_NORMALIZE_VALUE / extent)
        ).astype(np.float32)
    max_ext = float((p_max - p_min).max())
    if max_ext < 1e-8:
        return pts
    return (
        (pts - center) * (DATA_NORMALIZE_VALUE / max_ext)
    ).astype(np.float32)

def _normalize_heightmap_pts(pts: np.ndarray) -> np.ndarray:
    if not DATA_NORMALIZE or DATA_NORMALIZE_VALUE <= 0.0:
        return pts
    pts = pts.copy()
    if DATA_NORMALIZE_LOG:
        pts[:, 2] = np.log1p(np.maximum(pts[:, 2], 0.0))
    xy = pts[:, :2]
    xy_min = xy.min(axis=0)
    xy_max = xy.max(axis=0)
    xy_center = (xy_min + xy_max) * 0.5
    xy_ext = float((xy_max - xy_min).max())
    if xy_ext < 1e-8:
        xy_ext = 1.0
    pts[:, :2] = (xy - xy_center) * (DATA_NORMALIZE_VALUE / xy_ext)
    z = pts[:, 2]
    z_min, z_max = float(z.min()), float(z.max())
    z_center = (z_min + z_max) * 0.5
    z_ext = z_max - z_min
    if z_ext < 1e-8:
        z_ext = 1.0
    pts[:, 2] = (z - z_center) * (DATA_NORMALIZE_VALUE / z_ext)
    return pts.astype(np.float32)

def _npy_3d_to_polydata(
    data: np.ndarray, name: str,
) -> pv.PolyData:
    h, w, c = data.shape
    if c not in (3, 6):
        raise ValueError(
            f'Unsupported NPY shape for PolyData: {data.shape}'
        )
    pts = _normalize_pts(
        np.ascontiguousarray(
            data[..., :3].reshape(-1, 3).astype(np.float32)
        )
    )
    rgb = None
    if c == 6:
        raw_rgb = data[..., 3:6].reshape(-1, 3).astype(np.float32)
        if raw_rgb.max() <= 1.0:
            raw_rgb = (raw_rgb * 255.0).clip(0, 255)
        rgb = np.ascontiguousarray(raw_rgb.astype(np.uint8))
    if NPY_AS_POINTCLOUD:
        mesh_out = _npy_heightmap_to_pointcloud(pts, h, w, name)
    else:
        mesh_out = _npy_heightmap_to_mesh(pts, h, w, name)
    if rgb is not None:
        mesh_out.point_data['_rgb_packed'] = rgb
    return mesh_out

def _npy_heightmap_to_pointcloud(
    pts: np.ndarray, h: int, w: int, name: str,
) -> pv.PolyData:
    logger.debug('NPY point cloud %s: %dx%d -> %d pts', name, h, w, h * w)
    return pv.PolyData(pts)

def _npy_heightmap_to_mesh(
    pts: np.ndarray, h: int, w: int, name: str,
) -> pv.PolyData:
    idx = np.arange(h * w, dtype=np.int32).reshape(h, w)
    i0 = idx[:-1, :-1].ravel()
    i1 = idx[:-1, 1: ].ravel()
    i2 = idx[1: , 1: ].ravel()
    i3 = idx[1: , :-1].ravel()
    n = (h - 1) * (w - 1)
    three = np.full(n, 3, dtype=np.int32)
    faces = np.concatenate([
        np.column_stack([three, i0, i1, i2]).ravel(),
        np.column_stack([three, i0, i2, i3]).ravel(),
    ])
    logger.debug(
        'NPY height map %s: %dx%d -> %d pts, %d tris',
        name, h, w, h * w, n * 2,
    )
    return pv.PolyData(pts, faces)

def load_npy_as_polydata(path: str) -> pv.PolyData:
    data = np.load(path).astype(np.float32)

    if data.ndim == 2 and data.shape[1] == 3:
        pts = _normalize_pts(data)
        return pv.PolyData(np.ascontiguousarray(pts))

    if data.ndim == 2 and data.shape[1] == 6:
        pts = _normalize_pts(data[:, :3])
        mesh = pv.PolyData(np.ascontiguousarray(pts))
        rgb = data[:, 3:6]
        if rgb.max() <= 1.0:
            rgb = (rgb * 255.0).clip(0, 255)
        mesh.point_data['_rgb_packed'] = np.ascontiguousarray(
            rgb.astype(np.uint8)
        )
        return mesh

    if data.ndim == 2:
        h, w = data.shape
        x = np.linspace(0.0, float(w), w, dtype=np.float32)
        y = np.linspace(0.0, float(h), h, dtype=np.float32)
        xx, yy = np.meshgrid(x, y)
        raw = np.column_stack(
            [xx.ravel(), yy.ravel(), data.ravel()]
        ).astype(np.float32)
        pts = np.ascontiguousarray(_normalize_heightmap_pts(raw))
        name = os.path.basename(path)
        if NPY_AS_POINTCLOUD:
            return _npy_heightmap_to_pointcloud(pts, h, w, name)
        return _npy_heightmap_to_mesh(pts, h, w, name)

    if data.ndim == 3:
        return _npy_3d_to_polydata(data, os.path.basename(path))

    raise ValueError(
        f'Unsupported NPY shape for PolyData: {data.shape}'
    )

def _resolve_npz_pts_face_color(
    keys: set,
) -> tuple[str | None, str | None, str | None]:
    pts_key = next(
        (k for k in ('points', 'vertices', 'xyz') if k in keys), None
    )
    face_key = next(
        (k for k in ('faces', 'triangles', 'cells') if k in keys), None
    )
    color_key = next(
        (k for k in ('colors', 'color', 'rgb', 'rgba') if k in keys), None
    )
    return pts_key, face_key, color_key

def _npz_color_to_uint8(arr: np.ndarray) -> np.ndarray:
    if arr.dtype == np.uint8:
        return arr
    if arr.max() <= 1.0:
        arr = arr * 255.0
    return arr.clip(0, 255).astype(np.uint8)

def load_npz_as_polydata(path: str) -> pv.PolyData:
    data = np.load(path)
    keys = set(data.files)
    name = os.path.basename(path)

    if 'xyz' in keys and 'features' in keys:
        logger.debug('NPZ GS format detected: %s', name)
        mesh = pv.PolyData(_normalize_pts(data['xyz'].astype(np.float32)))
        if 'color' in keys:
            color = data['color']
            if color.ndim == 2 and color.shape[1] >= 3:
                mesh.point_data['_rgb_packed'] = np.ascontiguousarray(
                    color[:, :3], dtype=np.uint8
                )
        return mesh

    pts_key, face_key, color_key = _resolve_npz_pts_face_color(keys)

    if pts_key is not None:
        pts = _normalize_pts(
            np.ascontiguousarray(data[pts_key].astype(np.float32))
        )
        faces = data[face_key] if face_key else None
        mesh = pv.PolyData(pts, faces)
        if color_key is not None:
            color = _npz_color_to_uint8(data[color_key])
            if color.ndim == 2 and color.shape[1] >= 3:
                mesh.point_data['_rgb_packed'] = np.ascontiguousarray(
                    color[:, :3]
                )
        logger.debug(
            'NPZ mesh/pointcloud: %s pts=%d faces=%s',
            name, len(pts), face_key,
        )
        return mesh

    if not data.files:
        raise ValueError(f'Empty NPZ file: {path}')
    first_key = data.files[0]
    arr = data[first_key].astype(np.float32)
    logger.debug(
        'NPZ fallback to NPY shape handling: %s key=%s shape=%s',
        name, first_key, arr.shape,
    )
    if arr.ndim == 2 and arr.shape[1] == 3:
        pts = _normalize_pts(arr)
        return pv.PolyData(np.ascontiguousarray(pts))
    if arr.ndim == 2 and arr.shape[1] == 6:
        pts = _normalize_pts(arr[:, :3])
        mesh = pv.PolyData(np.ascontiguousarray(pts))
        rgb = arr[:, 3:6]
        if rgb.max() <= 1.0:
            rgb = (rgb * 255.0).clip(0, 255)
        mesh.point_data['_rgb_packed'] = np.ascontiguousarray(
            rgb.astype(np.uint8)
        )
        return mesh
    if arr.ndim == 2:
        h, w = arr.shape
        x = np.linspace(0.0, float(w), w, dtype=np.float32)
        y = np.linspace(0.0, float(h), h, dtype=np.float32)
        xx, yy = np.meshgrid(x, y)
        raw = np.column_stack(
            [xx.ravel(), yy.ravel(), arr.ravel()]
        ).astype(np.float32)
        pts = np.ascontiguousarray(_normalize_heightmap_pts(raw))
        if NPY_AS_POINTCLOUD:
            return _npy_heightmap_to_pointcloud(pts, h, w, name)
        return _npy_heightmap_to_mesh(pts, h, w, name)
    if arr.ndim == 3:
        return _npy_3d_to_polydata(arr, name)
    raise ValueError(
        f'Unsupported NPZ structure for PolyData: {path}'
    )
