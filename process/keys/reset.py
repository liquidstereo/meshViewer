import os
import logging
import numpy as np

from configs.settings import (
    SHOW_ANIMATION, SHOW_BACKFACE, SHOW_BBOX,
    SHOW_GRID, SHOW_LIGHTING, DEFAULT_SMOOTH, DEFAULT_TEXTURE,
    SHOW_TURNTABLE,
    ISO_COUNT_DEFAULT, REDUCTION_MESH,
    EDGE_FEATURE_ANGLE, VTX_SPATIAL_INTERVAL,
    OUTPUT_DIR_ROOT, SCREENSHOT_SUBDIR, SCREENSHOT_EXT,
    CAM_ZOOM_STEP, CAM_TRUCK_STEP, DEFAULT_ID_STYLE, VTX_LABEL_COLOR,
    NORMAL_COLOR_ENABLE_LIGHTING,
)
import core.theme as _theme_mod
from core.theme import invert_hex

from configs.keybinding import (
    KEY_RECORD,
    TURNTABLE_ROT_STEP,
    KEY_RESET_GROUP, KEY_CAM_RESET, KEY_CENTER_VIEW, KEY_CAM_PROJ, KEY_MESH_DEFAULT,
    KEY_SCREENSHOT, KEY_GRID, KEY_GRID_ONLY, KEY_TURNTABLE, KEY_HELP,
    KEY_PLAY, KEY_STEP_FWD, KEY_STEP_BWD,
    KEY_FIRST_FRAME, KEY_LAST_FRAME,
    KEY_ROT_XD, KEY_ROT_XU, KEY_ROT_YL, KEY_ROT_YR,
    KEY_OVERLAY, KEY_LOG_OVERLAY, KEY_STATUS_TEXT, KEY_SEQ_OVERLAY,
    KEY_ACTOR_NEXT, KEY_THEME,
    KEY_VIEW_FRONT, KEY_VIEW_BACK,
    KEY_VIEW_SIDE_L, KEY_VIEW_SIDE_R,
    KEY_VIEW_TOP, KEY_VIEW_BOTTOM,
    KEY_AXIS_SWAP,
    KEY_KP_ZOOM_IN, KEY_KP_ZOOM_OUT, KEY_KP_DOLLY_IN, KEY_KP_DOLLY_OUT,
    KEY_TRUCK_L, KEY_TRUCK_R, KEY_PEDESTAL_U, KEY_PEDESTAL_D,
)
from process.mode.labels import (
    LBL_GRID, LBL_TURNTABLE,
    LBL_PLAY_ON, LBL_PLAY_OFF,
    LBL_RESET_FULL, LBL_RESET_CAM, LBL_DEFAULT, LBL_CENTER_VIEW,
    LBL_TRUCK_L, LBL_TRUCK_R, LBL_PEDESTAL_U, LBL_PEDESTAL_D,
    LBL_SCREENSHOT, LBL_CAM_PARALLEL, LBL_CAM_PERSPECTIVE,
    LBL_VIEW_FRONT, LBL_VIEW_BACK,
    LBL_VIEW_SIDE_L, LBL_VIEW_SIDE_R,
    LBL_VIEW_TOP, LBL_VIEW_BOTTOM,
    LBL_FRAME_FIRST, LBL_FRAME_LAST,
    FMT_ACTOR_CYCLE,
    AXIS_SWAP_NAMES, FMT_AXIS_SWAP,
)
from process.init.exit_summary import emit_exit_summary, finalize_logs
from process.init.shutdown import graceful_shutdown
from process.scene.grid import setup_grid
from process.window.display import save_screenshot
from process.mode.default import apply_default_reset
from process.mode.common import _hex_to_rgb
from process.plotter.state import apply_mode_axes, resolve_id_style
from process.scene.lighting import apply_lighting
from process.window.toggle_info import toggle_info_overlay
from process.camera.utils import (
    restore_initial_camera, set_parallel_projection,
)
from process.keys import bind_key, dispatch_key
from process.render.live_record import request_toggle

logger = logging.getLogger(__name__)
_MAX_ELEVATION = 85.0

def _invert_color(r, g, b):
    return (1.0 - r, 1.0 - g, 1.0 - b)

def _reverse_lut(lut) -> None:
    n = lut.GetNumberOfTableValues()
    colors = [lut.GetTableValue(i) for i in range(n)]
    for i, c in enumerate(reversed(colors)):
        lut.SetTableValue(i, *c)
    lut.Modified()

def _invert_grid_colors(ax):
    for _get in (
        ax.GetXAxesLinesProperty, ax.GetYAxesLinesProperty,
        ax.GetZAxesLinesProperty,
        ax.GetXAxesGridlinesProperty, ax.GetYAxesGridlinesProperty,
        ax.GetZAxesGridlinesProperty,
    ):
        prop = _get()
        prop.SetColor(*_invert_color(*prop.GetColor()))
    for i in range(3):
        for _get in (ax.GetTitleTextProperty, ax.GetLabelTextProperty):
            prop = _get(i)
            prop.SetColor(*_invert_color(*prop.GetColor()))
    ax.Modified()

_THEME_REVERSED_LUTS = (
    '_depth_lut', '_pt_depth_lut', '_iso_lut', '_wire_lut',
)

def _recolor_vtx_labels(p) -> None:
    rgb = _hex_to_rgb(getattr(p, '_vtx_label_color', VTX_LABEL_COLOR))
    for actor in getattr(p, '_vtx_text_actors', ()):
        actor.GetTextProperty().SetColor(*rgb)

def _apply_theme_toggle(p):
    _theme_mod.toggle_theme()
    p.renderer.SetBackground(
        *_invert_color(*p.renderer.GetBackground())
    )
    bbox = getattr(p, '_bbox_actor', None)
    if bbox is not None:
        prop = bbox.GetProperty()
        prop.SetColor(*_invert_color(*prop.GetColor()))
    grid = getattr(p, '_grid_actor', None)
    if grid is not None:
        _invert_grid_colors(grid)
    for attr in ('_status_actor', '_mode_actor', '_log_actor'):
        actor = getattr(p, attr, None)
        if actor is not None:
            tp = actor.GetTextProperty()
            tp.SetColor(*_invert_color(*tp.GetColor()))
    help_actor = getattr(p, '_help_actor', None)
    if help_actor is not None:
        tp = help_actor.GetTextProperty()
        tp.SetColor(*_invert_color(*tp.GetColor()))
        tp.SetBackgroundColor(
            *_invert_color(*tp.GetBackgroundColor())
        )
    mapper = getattr(p, '_mesh_mapper', None)
    if mapper is not None and not mapper.GetScalarVisibility():
        prop = p._mesh_actor.GetProperty()
        prop.SetColor(*_invert_color(*prop.GetColor()))

    for attr in _THEME_REVERSED_LUTS:
        lut = getattr(p, attr, None)
        if lut is not None:
            _reverse_lut(lut)

    p._vtx_label_color = invert_hex(
        getattr(p, '_vtx_label_color', VTX_LABEL_COLOR)
    )
    _recolor_vtx_labels(p)
    p._prev_mode = None
    logger.info('Theme toggled: %s', _theme_mod.current_theme())
    p._needs_update = True

def register_cam_pan(p, trigger, set_mode) -> None:
    def _truck(dx):
        cam = p.renderer.GetActiveCamera()
        step = cam.GetDistance() * dx
        right = np.cross(
            np.array(cam.GetDirectionOfProjection()),
            np.array(cam.GetViewUp()),
        )
        norm = np.linalg.norm(right)
        if norm < 1e-8:
            return
        right = right / norm * step
        pos = np.array(cam.GetPosition())
        focal = np.array(cam.GetFocalPoint())
        cam.SetPosition(*(pos + right))
        cam.SetFocalPoint(*(focal + right))
        p.renderer.ResetCameraClippingRange()
        trigger()

    def _pedestal(dy):
        cam = p.renderer.GetActiveCamera()
        step = cam.GetDistance() * dy
        up = np.array(cam.GetViewUp())
        norm = np.linalg.norm(up)
        if norm < 1e-8:
            return
        up = up / norm * step
        pos = np.array(cam.GetPosition())
        focal = np.array(cam.GetFocalPoint())
        cam.SetPosition(*(pos + up))
        cam.SetFocalPoint(*(focal + up))
        p.renderer.ResetCameraClippingRange()
        trigger()

    dispatch_key(
        p._ctrl_key_dispatch, KEY_RECORD,
        lambda: request_toggle(p),
    )

    dispatch_key(
        p._ctrl_key_dispatch, KEY_TRUCK_L,
        lambda: (_truck(-CAM_TRUCK_STEP), set_mode(LBL_TRUCK_L)),
    )
    dispatch_key(
        p._ctrl_key_dispatch, KEY_TRUCK_R,
        lambda: (_truck(CAM_TRUCK_STEP), set_mode(LBL_TRUCK_R)),
    )
    dispatch_key(
        p._ctrl_key_dispatch, KEY_PEDESTAL_U,
        lambda: (_pedestal(CAM_TRUCK_STEP), set_mode(LBL_PEDESTAL_U)),
    )
    dispatch_key(
        p._ctrl_key_dispatch, KEY_PEDESTAL_D,
        lambda: (_pedestal(-CAM_TRUCK_STEP), set_mode(LBL_PEDESTAL_D)),
    )

def register(p, trigger, set_mode, total_len):
    p._total = total_len

    def _reset_all():
        p._idx = 0
        p._is_playing = SHOW_ANIMATION
        p._is_smooth = False
        p._smooth_cycle = 0
        p._pbr_with_tex = False
        p._is_smooth_shading = DEFAULT_SMOOTH
        p._is_wire = False
        p._is_tex = DEFAULT_TEXTURE
        p._is_grid = SHOW_GRID
        p._is_isoline = False
        p._isoline_visible = False
        p._is_iso_only = False
        p._is_lighting = SHOW_LIGHTING
        apply_lighting(p)
        p._is_backface = SHOW_BACKFACE
        p._vtx_mesh_hidden = False
        p._is_normal_color = False
        p._is_mesh_quality = False
        p._quality_cache = None
        p._quality_cache_n_faces = -1
        p._quality_cache_range = None
        p._quality_vtk_poly = None
        p._is_depth = False
        p._normal_color_lighting = NORMAL_COLOR_ENABLE_LIGHTING
        p._is_id = False
        p._id_region_key = None
        p._id_colors = None
        p._id_region_count = 0
        p._id_style = resolve_id_style(DEFAULT_ID_STYLE)
        p._is_vtx = False
        p._vtx_spatial_interval = VTX_SPATIAL_INTERVAL
        p._is_fnormal = False
        p._fnormal_mesh_hidden = True
        p._iso_count = ISO_COUNT_DEFAULT

        apply_mode_axes(p)
        p._reduction_mesh = REDUCTION_MESH
        p._prev_mode = None
        p._rot_elev = 0.0
        p._is_turntable = SHOW_TURNTABLE
        if SHOW_GRID:
            setup_grid(p)
        else:
            p.remove_bounds_axes()
        if hasattr(p, '_iso_actor'):
            p._iso_actor.VisibilityOff()
        if hasattr(p, '_wire_actor'):
            p._wire_actor.VisibilityOff()
        if hasattr(p, '_edge_actor'):
            p._edge_actor.VisibilityOff()
        if hasattr(p, '_outline_actor'):
            p._outline_actor.VisibilityOff()
        p._is_edge = False
        p._edge_visible = False
        p._edge_mesh_hidden = False
        p._is_outline = False
        p._outline_visible = False
        p._outline_mesh_hidden = True
        p._edge_feature_angle = EDGE_FEATURE_ANGLE
        p._wire_mesh_hidden = True
        if hasattr(p, '_fnormal_actor'):
            p._fnormal_actor.VisibilityOff()
        if hasattr(p, '_help_actor'):
            p._help_actor.VisibilityOff()
        p._wire_visible = False
        p._is_bbox = SHOW_BBOX
        if hasattr(p, '_bbox_actor'):
            if SHOW_BBOX:
                p._bbox_actor.VisibilityOn()
            else:
                p._bbox_actor.VisibilityOff()
        if hasattr(p, '_mesh_actor'):
            p._mesh_actor.VisibilityOn()
        if hasattr(p, '_vtx_sel_actor'):
            p._vtx_sel_actor.VisibilityOff()
        if hasattr(p, '_vtx_pick_text'):
            p._vtx_pick_text.VisibilityOff()
        p._vtx_world_pts = None
        p._vtx_indices = None
        p._current_view = None
        if hasattr(p, '_init_cam_pos'):
            p.camera_position = p._init_cam_pos
        cam = p.renderer.GetActiveCamera()
        if hasattr(p, '_init_parallel_proj'):
            set_parallel_projection(p, cam, p._init_parallel_proj)
        if hasattr(p, '_init_parallel_scale'):
            cam.SetParallelScale(p._init_parallel_scale)
        if hasattr(p, '_init_view_angle'):
            cam.SetViewAngle(p._init_view_angle)
        trigger()

    def _reset_camera():
        restore_initial_camera(p)
        trigger()

    def _center_view():
        cam = p.renderer.GetActiveCamera()
        pos = np.array(cam.GetPosition())
        focal = np.array(cam.GetFocalPoint())
        direction = pos - focal
        bounds = p.renderer.ComputeVisiblePropBounds()
        new_center = np.array([
            (bounds[0] + bounds[1]) / 2.0,
            (bounds[2] + bounds[3]) / 2.0,
            (bounds[4] + bounds[5]) / 2.0,
        ])
        cam.SetFocalPoint(*new_center)
        cam.SetPosition(*(new_center + direction))
        p.renderer.ResetCameraClippingRange()
        set_mode(LBL_CENTER_VIEW)
        trigger()

    def _set_mesh_default():
        apply_default_reset(p)
        trigger()

    def _rotate_camera(azimuth=0.0, elevation=0.0):
        cam = p.renderer.GetActiveCamera()
        if azimuth:
            cam.Azimuth(azimuth)
        if elevation:
            current = getattr(p, '_rot_elev', 0.0)
            new_elev = max(
                -_MAX_ELEVATION,
                min(_MAX_ELEVATION, current + elevation),
            )
            delta = new_elev - current
            if delta != 0.0:
                cam.Elevation(delta)
                p._rot_elev = new_elev
        p.renderer.ResetCameraClippingRange()
        trigger()

    def _toggle_grid():
        p._is_grid = not p._is_grid
        p._is_bbox = not p._is_bbox
        if p._is_grid:
            setup_grid(p)
        else:
            p.remove_bounds_axes()
        if hasattr(p, '_bbox_actor'):
            if p._is_bbox:
                p._bbox_actor.VisibilityOn()
            else:
                p._bbox_actor.VisibilityOff()
        set_mode(LBL_GRID if p._is_grid else '')
        trigger()

    def _toggle_grid_only():
        p._is_grid = not p._is_grid
        if p._is_grid:
            setup_grid(p)
        else:
            p.remove_bounds_axes()
        set_mode(LBL_GRID if p._is_grid else '')
        trigger()

    def _toggle_turntable():
        p._is_turntable = not getattr(p, '_is_turntable', False)
        set_mode(LBL_TURNTABLE if p._is_turntable else '')
        trigger()

    def _toggle_help():
        actor = getattr(p, '_help_actor', None)
        if actor is None:
            return
        if actor.GetVisibility():
            actor.VisibilityOff()
        else:
            actor.VisibilityOn()
        trigger()

    def _toggle_play():
        p._is_playing = not p._is_playing
        set_mode(LBL_PLAY_ON if p._is_playing else LBL_PLAY_OFF)
        trigger()

    def _reset_all_with_msg():
        _reset_all()
        set_mode(LBL_RESET_FULL)

    def _reset_camera_with_msg():
        _reset_camera()
        set_mode(LBL_RESET_CAM)

    def _set_mesh_default_with_msg():
        _set_mesh_default()
        set_mode(LBL_DEFAULT)

    bind_key(p, KEY_RESET_GROUP, _reset_all_with_msg)
    bind_key(p, KEY_CAM_RESET, _reset_camera_with_msg)
    bind_key(p, KEY_CENTER_VIEW, _center_view)
    bind_key(p, KEY_MESH_DEFAULT, _set_mesh_default_with_msg)
    bind_key(p, KEY_GRID, _toggle_grid)
    bind_key(p, KEY_GRID_ONLY, _toggle_grid_only)
    bind_key(p, KEY_TURNTABLE, _toggle_turntable)
    bind_key(p, KEY_HELP, _toggle_help)

    def _take_screenshot():
        name = getattr(p, '_input_name', 'screenshot')
        scr_dir = os.path.join(OUTPUT_DIR_ROOT, SCREENSHOT_SUBDIR)
        os.makedirs(scr_dir, exist_ok=True)
        path = os.path.join(
            scr_dir, f'{name}_screenshot.{SCREENSHOT_EXT}'
        )
        try:
            save_screenshot(p, path)
            logger.info('Screenshot saved: %s', path)
            set_mode(LBL_SCREENSHOT)
        except Exception as e:
            logger.error('Screenshot failed: %s', e)

    def _toggle_cam_proj():
        cam = p.renderer.GetActiveCamera()
        is_parallel = cam.GetParallelProjection()
        set_parallel_projection(p, cam, not is_parallel)
        label = LBL_CAM_PARALLEL if not is_parallel else LBL_CAM_PERSPECTIVE
        set_mode(label)
        trigger()

    def _toggle_overlay():
        toggle_info_overlay(p)
        trigger()

    def _toggle_log_overlay():
        p._is_log_visible = not getattr(p, '_is_log_visible', True)
        trigger()

    def _toggle_status_text():
        p._is_status_visible = not getattr(p, '_is_status_visible', True)
        trigger()

    def _toggle_seq_overlay():
        overlay = getattr(p, '_seq_overlay', None)
        if overlay is None:
            return
        visible = not bool(overlay._renderer.GetDraw())
        overlay.set_visible(visible)
        trigger()

    dispatch_key(p._special_key_dispatch, KEY_SCREENSHOT, _take_screenshot)
    bind_key(p, KEY_CAM_PROJ, _toggle_cam_proj)
    bind_key(p, KEY_OVERLAY, _toggle_overlay)
    bind_key(p, KEY_LOG_OVERLAY, _toggle_log_overlay)
    bind_key(p, KEY_STATUS_TEXT, _toggle_status_text)
    bind_key(p, KEY_SEQ_OVERLAY, _toggle_seq_overlay)
    bind_key(p, KEY_PLAY, _toggle_play)
    bind_key(p, KEY_STEP_FWD, lambda: (
        setattr(p, '_idx', (p._idx + 1) % total_len),
        setattr(p, '_is_playing', False),
        trigger(),
    ))
    bind_key(p, KEY_STEP_BWD, lambda: (
        setattr(p, '_idx', (p._idx - 1) % total_len),
        setattr(p, '_is_playing', False),
        trigger(),
    ))
    bind_key(p, KEY_ROT_YL, lambda: _rotate_camera(azimuth=-TURNTABLE_ROT_STEP))
    bind_key(p, KEY_ROT_YR, lambda: _rotate_camera(azimuth=TURNTABLE_ROT_STEP))
    bind_key(p, KEY_ROT_XD, lambda: _rotate_camera(elevation=-TURNTABLE_ROT_STEP))
    bind_key(p, KEY_ROT_XU, lambda: _rotate_camera(elevation=TURNTABLE_ROT_STEP))

    def _go_first_frame():
        p._idx = 0
        p._is_playing = False
        set_mode(LBL_FRAME_FIRST)
        trigger()

    def _go_last_frame():
        p._idx = total_len - 1
        p._is_playing = False
        set_mode(LBL_FRAME_LAST)
        trigger()

    def _apply_view(direction, viewup, label):
        if getattr(p, '_current_view', None) == label:
            p._is_turntable = SHOW_TURNTABLE
            _reset_camera()
            set_mode(LBL_RESET_CAM)
            return
        p._is_turntable = False
        cam = p.renderer.GetActiveCamera()
        fp = np.array(cam.GetFocalPoint())
        dist = cam.GetDistance()
        cam.SetPosition(*(fp + np.array(direction) * dist))
        cam.SetViewUp(*viewup)
        set_parallel_projection(p, cam, True)
        p.renderer.ResetCamera()
        p._current_view = label
        set_mode(label)
        trigger()

    def _cycle_actor():
        _CYCLE_ATTRS = (
            '_mesh_actor', '_iso_actor', '_wire_actor',
            '_edge_actor', '_outline_actor', '_bbox_actor',
            '_vtx_point_actor', '_fnormal_actor', '_vtx_sel_actor',
        )
        actor_list = [
            getattr(p, attr) for attr in _CYCLE_ATTRS
            if getattr(p, attr, None) is not None
        ]
        n = len(actor_list)
        if n <= 1:
            trigger()
            return
        idx = getattr(p, '_actor_cycle_idx', 0) % n
        for i, act in enumerate(actor_list):
            act.SetVisibility(i == idx)
        p._actor_cycle_idx = (idx + 1) % n
        set_mode(FMT_ACTOR_CYCLE.format(idx + 1, n))
        trigger()

    def _zoom(factor):
        cam = p.renderer.GetActiveCamera()
        if cam.GetParallelProjection():
            cam.SetParallelScale(cam.GetParallelScale() / factor)
        else:
            cam.Zoom(factor)
        p.renderer.ResetCameraClippingRange()
        trigger()

    def _dolly(factor):
        cam = p.renderer.GetActiveCamera()
        cam.Dolly(factor)
        p.renderer.ResetCameraClippingRange()
        trigger()

    register_cam_pan(p, trigger, set_mode)

    dispatch_key(p._special_key_dispatch, KEY_FIRST_FRAME, _go_first_frame)
    dispatch_key(p._special_key_dispatch, KEY_LAST_FRAME, _go_last_frame)
    dispatch_key(p._special_key_dispatch, KEY_ACTOR_NEXT, _cycle_actor)
    dispatch_key(
        p._special_key_dispatch, KEY_THEME,
        lambda: _apply_theme_toggle(p),
    )
    dispatch_key(
        p._special_key_dispatch, KEY_VIEW_FRONT,
        lambda: _apply_view((0, 0, 1), (0, 1, 0), LBL_VIEW_FRONT),
    )
    dispatch_key(
        p._special_key_dispatch, KEY_VIEW_BACK,
        lambda: _apply_view((0, 0, -1), (0, 1, 0), LBL_VIEW_BACK),
    )
    dispatch_key(
        p._special_key_dispatch, KEY_VIEW_SIDE_L,
        lambda: _apply_view((-1, 0, 0), (0, 1, 0), LBL_VIEW_SIDE_L),
    )
    dispatch_key(
        p._special_key_dispatch, KEY_VIEW_SIDE_R,
        lambda: _apply_view((1, 0, 0), (0, 1, 0), LBL_VIEW_SIDE_R),
    )
    dispatch_key(
        p._special_key_dispatch, KEY_VIEW_TOP,
        lambda: _apply_view((0, 1, 0), (0, 0, -1), LBL_VIEW_TOP),
    )
    dispatch_key(
        p._special_key_dispatch, KEY_VIEW_BOTTOM,
        lambda: _apply_view((0, -1, 0), (0, 0, 1), LBL_VIEW_BOTTOM),
    )

    def _cycle_axis_swap():
        p._axis_swap = (getattr(p, '_axis_swap', 0) + 1) % len(
            AXIS_SWAP_NAMES
        )
        p._prev_mode = None
        p._last_mesh_for_normal = None
        p._axis_swap_cache_key = None
        p._needs_update = True
        label = FMT_AXIS_SWAP.format(AXIS_SWAP_NAMES[p._axis_swap])
        set_mode(label)
        logger.info('Axis swap: %s', AXIS_SWAP_NAMES[p._axis_swap])
        trigger()

    dispatch_key(
        p._special_key_dispatch, KEY_AXIS_SWAP, _cycle_axis_swap
    )
    bind_key(p, KEY_KP_ZOOM_IN,   lambda: _zoom(CAM_ZOOM_STEP))
    bind_key(p, KEY_KP_ZOOM_OUT,  lambda: _zoom(1.0 / CAM_ZOOM_STEP))
    bind_key(p, KEY_KP_DOLLY_IN,  lambda: _dolly(CAM_ZOOM_STEP))
    bind_key(p, KEY_KP_DOLLY_OUT, lambda: _dolly(1.0 / CAM_ZOOM_STEP))

    def _force_exit():

        graceful_shutdown(p, 'esc')

        input_name = getattr(p, '_input_name', '?')
        total = getattr(p, '_total', 0)
        save_counter = getattr(p, '_save_counter', 0)
        finalize_logs(
            input_name, total, getattr(p, '_start_time', None),
            save_counter, getattr(p, '_save_path', None),
        )

        save_sink = getattr(p, '_save_sink', None)
        sink_target = (
            save_sink.display_target if save_sink is not None else None
        )
        emit_exit_summary(input_name, total, save_counter, sink_target)
        os._exit(0)

    p.add_key_event('Escape', _force_exit)
