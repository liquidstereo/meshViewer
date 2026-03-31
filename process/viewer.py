import os
import time
import logging
import numpy as np
import pyvista as pv

from pyvista.plotting import Plotter

import configs.defaults as _cfg

from configs.defaults import (
    RENDER_FXAA, WINDOW_MONITOR_INDEX,
    GRID_FONT_FAMILY, AUDIO_GRID_TEXT_COLOR,
    RENDER_MSAA_SAMPLES, WINDOW_TITLE,
    COLOR_BG, AUDIO_TARGET_FPS,
    AUDIO_FREQ_NORM_MAX, AUDIO_GRID_Y_MAX, AUDIO_FREQ_SAMPLES,
    AUDIO_TIME_RANGE, AUDIO_FOCUS_FREQ_RANGE,
    AUDIO_COLOR_GRID, GRID_WIDTH,
    DEFAULT_GRID, AUDIO_ISO_AXIS, AUDIO_COLOR_AXIS,
    AUDIO_ISO_COUNT_DEFAULT, STARTUP_AUDIO_MODE,
)
from configs.colorize import Msg
from process.init import init_vtk, log_session_start  # noqa: F401
from process.load import FrameBuffer, show_loading, hide_loading
from process.load.loading_files import load_audio_data
from process.plotter import (
    build_plotter,
    init_plotter_state,
    setup_camera as _setup_camera,
)
from process.scene import (  # noqa: F401
    setup_scene, apply_lighting, setup_hdri, enable_hdri, init_actors,
    setup_axes_marker,
)
from process.scene.grid import _apply_grid_line_width
from process.window import center_window, apply_overlay_visibility, get_window_sizes
from process.overlay import (
    init_overlays,  # noqa: F401
    init_sequence_overlay,
)
from process.overlay.hud_texts import update_colorbar
from process.overlay.sequence import load_seq_files
from process.render import render_loop
from process.keymapping import apply_key_filter_style, register_callbacks
from process.audio import WaterfallRenderer
from process.mode.audio import exec_audio_viewer  # noqa: F401

logger = logging.getLogger(__name__)

def load_files(obj_files: list, args) -> FrameBuffer:

    log_session_start(obj_files, args)

    t = time.perf_counter()
    buffer = FrameBuffer(
        obj_files, args.smooth,
        preload_all=args.preload_all,
        no_cache=args.no_cache,
    )
    logger.debug('FrameBuffer init: %.4fs', time.perf_counter() - t)

    if args.save:
        os.makedirs(args.save, exist_ok=True)
        logger.info('Save output dir: %s', args.save)
    return buffer

def create_plotter() -> Plotter:
    t = time.perf_counter()
    plotter = build_plotter()
    logger.debug('Plotter init: %.4fs', time.perf_counter() - t)
    return plotter

def setup_cam(plotter, buffer) -> None:
    mesh0, _ = buffer.first_frame
    _setup_camera(plotter, mesh0)

def build_scene(plotter) -> None:
    t = time.perf_counter()
    setup_scene(plotter)
    logger.debug('setup_scene: %.4fs', time.perf_counter() - t)

def register_keys(plotter, total: int) -> None:
    t = time.perf_counter()
    register_callbacks(plotter, total)
    logger.debug('register_callbacks: %.4fs', time.perf_counter() - t)

def setup_window(plotter) -> None:
    apply_lighting(plotter)
    setup_hdri(plotter)
    if getattr(plotter, '_is_smooth', False):
        enable_hdri(plotter)
    hide_loading()

def show_window(plotter) -> None:
    t = time.perf_counter()
    center_window(plotter, WINDOW_MONITOR_INDEX)
    plotter.show(interactive_update=True)
    if RENDER_FXAA:
        plotter.renderer.SetUseFXAA(True)
    apply_key_filter_style(plotter)
    logger.debug('plotter.show: %.4fs', time.perf_counter() - t)

def load_seq_overlay(plotter, args, total: int) -> None:
    seq_files = load_seq_files(args, total)
    if seq_files:
        init_sequence_overlay(plotter, seq_files)

def apply_hide_info(plotter) -> None:
    apply_overlay_visibility(plotter)

def run_loop(plotter, buffer) -> None:
    try:
        render_loop(plotter, buffer)
    except KeyboardInterrupt:
        pass
    finally:
        buffer.cleanup()

def create_audio_plotter(args) -> pv.Plotter:
    t = time.perf_counter()
    pv.global_theme.font.family = GRID_FONT_FAMILY
    pv.global_theme.font.color = AUDIO_GRID_TEXT_COLOR
    pv.global_theme.allow_empty_mesh = True
    pv.global_theme.multi_samples = RENDER_MSAA_SAMPLES

    _win_w, _win_h = get_window_sizes(WINDOW_MONITOR_INDEX)
    plotter = pv.Plotter(
        title=WINDOW_TITLE,
        window_size=(_win_w, _win_h),
    )
    plotter.set_background(COLOR_BG)
    pv.set_new_attribute(plotter, 'pickpoint', np.zeros((1, 3)))
    plotter._special_key_dispatch = {}
    plotter._ctrl_key_dispatch = {}
    logger.debug('create_audio_plotter: %.4fs', time.perf_counter() - t)
    return plotter

def load_audio(
    audio_path: str,
    start: float,
    end: float | None,
) -> tuple:
    t = time.perf_counter()
    result = load_audio_data(audio_path, start, end, AUDIO_TARGET_FPS)
    logger.debug('load_audio: %.4fs', time.perf_counter() - t)
    return result

def show_audio_window(plotter) -> None:
    t = time.perf_counter()
    hide_loading()
    center_window(plotter, WINDOW_MONITOR_INDEX)
    plotter.show(interactive_update=True, auto_close=False)
    if RENDER_FXAA:
        plotter.renderer.SetUseFXAA(True)
    if plotter.iren:
        plotter.iren.initialize()
    apply_key_filter_style(plotter)
    logger.debug('show_audio_window: %.4fs', time.perf_counter() - t)

def build_audio_scene(
    plotter,
    actual_sr: float,
    hop_len: int,
    global_max: float,
    args,
) -> tuple:
    t = time.perf_counter()
    grid_bounds = [
        0, AUDIO_FREQ_NORM_MAX,
        0, AUDIO_GRID_Y_MAX,
        0, AUDIO_GRID_Y_MAX,
    ]
    _f_s, _f_e = AUDIO_FOCUS_FREQ_RANGE
    _freq_unit = (
        (_f_e - _f_s) * actual_sr / 512 / AUDIO_FREQ_NORM_MAX
    )
    _y_unit = global_max / AUDIO_GRID_Y_MAX
    _t_unit = AUDIO_TIME_RANGE / AUDIO_GRID_Y_MAX
    if DEFAULT_GRID:
        plotter.show_grid(
            xtitle=f'FREQUENCY (X{_freq_unit:.1f}Hz)',
            ytitle=f'INTENSITY (X{_y_unit:.2f}dB)',
            ztitle=f'TIME (X{_t_unit:.2f}s)',
            bounds=grid_bounds, color=AUDIO_COLOR_GRID,
            font_size=_cfg.AUDIO_AXIS_LABEL_FONT_SIZE, location='outer',
        )
    _grid_actor = getattr(
        plotter.renderer, 'cube_axes_actor', None
    )
    if _grid_actor is not None:
        _apply_grid_line_width(_grid_actor, GRID_WIDTH)
    plotter._grid_actor = _grid_actor

    norm_x = np.linspace(0, AUDIO_FREQ_NORM_MAX, AUDIO_FREQ_SAMPLES)
    win_size = int(
        (AUDIO_TIME_RANGE * actual_sr) / (hop_len * 2)
    )
    x_grid, z_grid = np.meshgrid(
        norm_x, np.linspace(0, AUDIO_GRID_Y_MAX, win_size)
    )

    renderer = WaterfallRenderer(
        plotter, x_grid, z_grid, global_max,
        STARTUP_AUDIO_MODE, AUDIO_ISO_AXIS, AUDIO_COLOR_AXIS,
        AUDIO_ISO_COUNT_DEFAULT,
    )
    logger.debug('build_audio_scene: %.4fs', time.perf_counter() - t)
    return renderer, x_grid, _grid_actor

def init_audio_actors(plotter, renderer) -> None:
    t = time.perf_counter()
    renderer.init_actors()
    plotter._bbox_actor = renderer.bbox_actor
    logger.debug('init_audio_actors: %.4fs', time.perf_counter() - t)

def setup_audio_window(plotter, renderer, cam_cbs: dict) -> None:
    t = time.perf_counter()
    setup_axes_marker(plotter)
    cam_cbs['reset']()
    update_colorbar(plotter)

    def _on_pre_render(obj, event) -> None:
        if (renderer.mode != 'EDGE'
                or renderer._edge_filter is None
                or renderer.main_actor is None):
            return
        lo, hi = renderer._set_edge_scalars()
        renderer._edge_filter.Update()
        renderer.main_actor.mapper.SetScalarRange(lo, hi)
        plotter._cmap_range = (lo, hi)

    plotter.renderer.AddObserver('StartEvent', _on_pre_render)
    plotter._n_points = renderer.base_poly.n_points
    plotter._n_faces = renderer.base_poly.n_faces_strict
    plotter._n_cells = 0
    logger.debug('setup_audio_window: %.4fs', time.perf_counter() - t)
