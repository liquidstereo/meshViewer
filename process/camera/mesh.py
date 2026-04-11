import logging
import numpy as np

from configs.defaults import (
    COLOR_BG, CAM_DIST_FACTOR, CAM_UP_VECTOR, NORM_SIZE,
)

logger = logging.getLogger(__name__)

_AXIS_SWAP_ORDER = [
    None,
    (0, 2, 1),
    (2, 1, 0),
    (1, 0, 2),
]

def _transform_pts(pts: np.ndarray, swap_idx: int, reverse: tuple) -> np.ndarray:
    result = pts.copy()
    rx, ry, rz = reverse
    if rx:
        result[:, 0] *= -1
    if ry:
        result[:, 1] *= -1
    if rz:
        result[:, 2] *= -1
    if swap_idx:
        result = result[:, list(_AXIS_SWAP_ORDER[swap_idx])]
    return result

def setup_camera(plotter, mesh0) -> None:
    b = mesh0.bounds
    c = mesh0.center
    extents = [b[1] - b[0], b[3] - b[2], b[5] - b[4]]
    s = NORM_SIZE / max(extents) if max(extents) > 0 else 1.0
    cx, cy, cz = c[0], c[1], c[2]
    dist = NORM_SIZE * CAM_DIST_FACTOR
    cam_pos = [(cx, cy, cz + dist), (cx, cy, cz), CAM_UP_VECTOR]

    plotter._norm_scale = s
    plotter._norm_center = [cx, cy, cz]
    plotter._norm_bounds = (
        s * b[0] + (1 - s) * cx, s * b[1] + (1 - s) * cx,
        s * b[2] + (1 - s) * cy, s * b[3] + (1 - s) * cy,
        s * b[4] + (1 - s) * cz, s * b[5] + (1 - s) * cz,
    )
    plotter.camera_position = cam_pos
    plotter._init_cam_pos = cam_pos
    cam = plotter.renderer.GetActiveCamera()
    plotter._init_parallel_scale = cam.GetParallelScale()
    plotter._init_view_angle = cam.GetViewAngle()
    plotter.set_background(COLOR_BG)
    logger.debug(
        'setup_camera: scale=%.4f center=%s', s, plotter._norm_center
    )

def apply_startup_axis_to_camera(plotter, mesh0) -> None:
    swap = getattr(plotter, '_axis_swap', 0)
    reverse = getattr(plotter, '_axis_reverse', (False, False, False))
    if swap == 0 and not any(reverse):
        return

    pts_t = _transform_pts(mesh0.points, swap, reverse)
    mn = pts_t.min(axis=0)
    mx = pts_t.max(axis=0)
    cx, cy, cz = ((mn + mx) / 2.0).tolist()
    extents = (mx - mn).tolist()
    max_ext = max(extents) if max(extents) > 0 else 1.0
    s = NORM_SIZE / max_ext
    dist = NORM_SIZE * CAM_DIST_FACTOR

    up_orig = np.array([[0.0, 1.0, 0.0]])
    up_t = _transform_pts(up_orig, swap, reverse)[0]
    up_norm = np.linalg.norm(up_t)
    if up_norm > 1e-8:
        up_t = up_t / up_norm
    else:
        up_t = np.array([0.0, 1.0, 0.0])

    extent_arr = mx - mn

    abs_up = np.abs(up_t)
    up_axis = int(np.argmax(abs_up))
    remaining = [(i, extent_arr[i]) for i in range(3) if i != up_axis]
    view_axis = max(remaining, key=lambda x: x[1])[0]
    view_dir = np.zeros(3)
    view_dir[view_axis] = dist

    focal = np.array([cx, cy, cz])
    cam_pos_pt = focal + view_dir
    cam_pos = [
        tuple(cam_pos_pt.tolist()),
        (cx, cy, cz),
        tuple(up_t.tolist()),
    ]

    plotter._norm_scale = s
    plotter._norm_center = [cx, cy, cz]
    plotter._norm_bounds = (
        s * mn[0] + (1 - s) * cx, s * mx[0] + (1 - s) * cx,
        s * mn[1] + (1 - s) * cy, s * mx[1] + (1 - s) * cy,
        s * mn[2] + (1 - s) * cz, s * mx[2] + (1 - s) * cz,
    )
    plotter.camera_position = cam_pos
    plotter._init_cam_pos = cam_pos
    cam = plotter.renderer.GetActiveCamera()
    plotter._init_parallel_scale = cam.GetParallelScale()
    plotter._init_view_angle = cam.GetViewAngle()
    logger.debug(
        'apply_startup_axis_to_camera: scale=%.4f center=[%.3f %.3f %.3f] '
        'up=%s view_axis=%s',
        s, cx, cy, cz, up_t.tolist(), ('X', 'Y', 'Z')[view_axis],
    )
