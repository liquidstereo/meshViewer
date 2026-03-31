import logging

from configs.defaults import (
    COLOR_BG, CAM_DIST_FACTOR, CAM_UP_VECTOR, NORM_SIZE,
)

logger = logging.getLogger(__name__)

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
