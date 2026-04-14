import logging

import numpy as np
import pyvista as pv

from configs.settings import (
    AUDIO_FADE_WIDTH,
    AUDIO_GRID_Y_MAX,
    AUDIO_MESH_SMOOTHING_ITERS,
    AUDIO_MESH_Y_OFFSET,
    AUDIO_MESH_Y_CUTOFF,
    AUDIO_ISO_OFFSET,
)
from process.mode.common import _get_cam_dir

logger = logging.getLogger(__name__)

def apply_boundary_fade(buffer: np.ndarray) -> np.ndarray:
    rows, cols = buffer.shape

    def _window(size: int, fade_rate: float) -> np.ndarray:
        fade_size = int(size * fade_rate)
        win = np.ones(size)
        if fade_size > 0:
            ramp = np.sin(
                np.linspace(0, np.pi / 2, fade_size)
            ) ** 2
            win[:fade_size] = ramp
            win[-fade_size:] = ramp[::-1]
        return win

    return buffer * np.outer(
        _window(rows, AUDIO_FADE_WIDTH),
        _window(cols, AUDIO_FADE_WIDTH),
    )

def process_geometry(
    buffer: np.ndarray,
    x_grid: np.ndarray,
    z_grid: np.ndarray,
    global_max: float,
) -> pv.PolyData:
    f_buf = apply_boundary_fade(buffer)
    y_data = (
        f_buf / global_max * AUDIO_GRID_Y_MAX
        if global_max > 0 else f_buf
    )
    grid = pv.StructuredGrid(x_grid, y_data, z_grid)
    poly = grid.extract_surface(algorithm='dataset_surface')
    if AUDIO_MESH_SMOOTHING_ITERS > 0:
        poly = poly.smooth_taubin(
            n_iter=AUDIO_MESH_SMOOTHING_ITERS,
            pass_band=0.04,
            boundary_smoothing=True,
            feature_smoothing=False,
        )
    pts = poly.points.copy()
    pts[:, 1] = np.maximum(pts[:, 1], 0.0)
    pts[:, 1] += AUDIO_MESH_Y_OFFSET
    pts[pts[:, 1] < AUDIO_MESH_Y_CUTOFF, 1] = 0.0
    poly.points = pts
    return poly

def update_isoline_and_color(
    plotter: pv.Plotter,
    base_poly: pv.PolyData,
    target_poly: pv.PolyData,
    iso_axis: str,
    color_axis: str,
    iso_count: int,
) -> tuple | None:
    _AXIS_IDX = {'X': 0, 'Y': 1, 'Z': 2}

    if iso_axis == 'CAM':
        cam_dir = _get_cam_dir(plotter)
        shape_scalars = -(
            base_poly.points @ cam_dir
        ).astype(np.float32)
    else:
        shape_scalars = base_poly.points[
            :, _AXIS_IDX[iso_axis]
        ].astype(np.float32)

    try:
        new_iso = base_poly.contour(
            isosurfaces=iso_count, scalars=shape_scalars
        )
    except Exception as e:
        logger.warning('Contour generation failed: %s', e)
        new_iso = pv.PolyData(
            np.array([[0, 0, 0]], dtype=np.float32)
        )

    if new_iso.n_points > 0:
        pts = new_iso.points.copy()
        pts[:, 1] += AUDIO_ISO_OFFSET
        new_iso.points = pts

    scalar_range = None
    if new_iso.n_points > 0:
        if color_axis == 'CAM':
            if iso_axis != 'CAM':
                cam_dir = _get_cam_dir(plotter)
            color_scalars = -(
                new_iso.points @ cam_dir
            ).astype(np.float32)
        else:
            color_scalars = new_iso.points[
                :, _AXIS_IDX[color_axis]
            ].astype(np.float32)
        scalar_range = (
            float(color_scalars.min()),
            float(color_scalars.max()),
        )
        new_iso.point_data['dynamic_colors'] = color_scalars
        new_iso.set_active_scalars('dynamic_colors')

    target_poly.shallow_copy(new_iso)
    return scalar_range
