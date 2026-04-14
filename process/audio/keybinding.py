import os
import time
import logging

import numpy as np

from configs.colorize import Msg
from configs.settings import (
    LOG_DIR, ISO_COUNT_STEP, EDGE_FEATURE_ANGLE_STEP,
    STARTUP_AUDIO_MODE, DEFAULT_BACKFACE, DEFAULT_COLORBAR,
    AUDIO_SEEK_STEP, OUTPUT_DIR_ROOT, SCREENSHOT_SUBDIR,
    AUDIO_ISO_AXIS, AUDIO_COLOR_AXIS,
    AUDIO_ISO_COUNT_DEFAULT, AUDIO_EDGE_FEATURE_ANGLE,
)
from configs.keybinding import (
    KEY_CAM_RESET, KEY_TURNTABLE,
    KEY_AXIS_NEXT, KEY_AXIS_PREV, KEY_INC, KEY_DEC,
    KEY_CAM_PROJ, KEY_CENTER_VIEW, KEY_SCREENSHOT,
    KEY_KP_ZOOM_IN, KEY_KP_ZOOM_OUT,
    KEY_KP_DOLLY_IN, KEY_KP_DOLLY_OUT,
    KEY_ROT_YL, KEY_ROT_YR, KEY_ROT_XD, KEY_ROT_XU,
    KEY_OVERLAY, KEY_BACKFACE,
    KEY_MESH_DEFAULT, KEY_SMOOTH_SHADING,
    KEY_VTX, KEY_WIRE, KEY_SMOOTH, KEY_ISO,
    KEY_LIGHT, KEY_MESH_QUALITY, KEY_FACE_NORMAL,
    KEY_DEPTH, KEY_EDGE,
    KEY_NORMAL_COLOR, KEY_GRID, KEY_ACTOR_NEXT, KEY_PLAY,
    KEY_STEP_FWD, KEY_STEP_BWD,
    KEY_FIRST_FRAME, KEY_LAST_FRAME, KEY_HELP,
    KEY_VIEW_FRONT, KEY_VIEW_BACK,
    KEY_VIEW_SIDE_L, KEY_VIEW_SIDE_R,
    KEY_VIEW_TOP, KEY_VIEW_BOTTOM,
)
from process.mode.labels import (
    LBL_VIEW_FRONT, LBL_VIEW_BACK,
    LBL_VIEW_SIDE_L, LBL_VIEW_SIDE_R,
    LBL_VIEW_TOP, LBL_VIEW_BOTTOM,
    AXIS_NAMES, FMT_NORMAL_AXIS,
)
from process.scene.lighting import apply_lighting
from process.keys.reset import register_cam_pan
from process.keys import dispatch_key
from process.window.display import save_screenshot
from process.window.toggle_info import toggle_info_overlay
from process.overlay.hud_texts import update_colorbar
from process.init.session_log import log_session_end
from process.audio.state import AudioContext

logger = logging.getLogger(__name__)

def register_audio_keys(
    plotter,
    renderer,
    ctx: AudioContext,
    cam_cbs: dict,
    set_mode_msg: callable,
) -> None:
    def _screenshot() -> None:
        sdir = os.path.join(OUTPUT_DIR_ROOT, SCREENSHOT_SUBDIR)
        os.makedirs(sdir, exist_ok=True)
        fname = os.path.join(
            sdir, f'{ctx.base_name}_screenshot.png'
        )
        save_screenshot(plotter, fname)
        logger.info('Screenshot saved: %s', fname)

    def _cycle_axis(delta: int) -> None:
        if renderer.mode == 'MESH':
            plotter._is_lighting = not getattr(
                plotter, '_is_lighting', False
            )
            apply_lighting(plotter)
            state = 'ON' if plotter._is_lighting else 'OFF'
            set_mode_msg(f'LIGHTING: {state}')
            logger.info('Audio lighting: %s', state)
        elif renderer.mode == 'DEPTH':
            renderer._depth_axis = (
                (renderer._depth_axis + delta)
                % len(AXIS_NAMES)
            )
            axis_name = AXIS_NAMES[renderer._depth_axis]
            set_mode_msg(f'DEPTH.AXIS: {axis_name}')
            logger.info('Depth axis: %s', axis_name)
        elif renderer.mode in ('ISOLINE', 'WIREFRAME'):
            idx = AXIS_NAMES.index(renderer._iso_axis)
            renderer._iso_axis = (
                AXIS_NAMES[(idx + delta) % len(AXIS_NAMES)]
            )
            set_mode_msg(f'ISO AXIS: {renderer._iso_axis}')
            logger.info('ISO axis: %s', renderer._iso_axis)
        elif renderer.mode == 'FACE_NORMAL':
            renderer._fnormal_axis = (
                (renderer._fnormal_axis + delta) % 4
            )
            axis_name = AXIS_NAMES[renderer._fnormal_axis]
            set_mode_msg(FMT_NORMAL_AXIS.format(axis_name))
            logger.info('Face normal axis: %s', axis_name)

    def _inc_iso() -> None:
        renderer._iso_count = max(
            1, renderer._iso_count + ISO_COUNT_STEP
        )
        set_mode_msg(f'ISO COUNT: {renderer._iso_count}')
        logger.info('ISO count: %d', renderer._iso_count)

    def _dec_iso() -> None:
        renderer._iso_count = max(
            1, renderer._iso_count - ISO_COUNT_STEP
        )
        set_mode_msg(f'ISO COUNT: {renderer._iso_count}')
        logger.info('ISO count: %d', renderer._iso_count)

    def _kp_inc() -> None:
        if (renderer.mode == 'EDGE'
                and renderer._edge_filter is not None):
            new_angle = round(
                min(180.0,
                    renderer._edge_feature_angle
                    + EDGE_FEATURE_ANGLE_STEP),
                1,
            )
            renderer._edge_feature_angle = new_angle
            renderer._edge_filter.SetFeatureAngle(new_angle)
            set_mode_msg(f'EDGE.ANGLE: {new_angle:.1f}')
            logger.info('Audio edge angle: %.1f', new_angle)
            plotter.render()
        elif renderer.mode in ('ISOLINE', 'WIREFRAME'):
            _inc_iso()

    def _kp_dec() -> None:
        if (renderer.mode == 'EDGE'
                and renderer._edge_filter is not None):
            new_angle = round(
                max(1.0,
                    renderer._edge_feature_angle
                    - EDGE_FEATURE_ANGLE_STEP),
                1,
            )
            renderer._edge_feature_angle = new_angle
            renderer._edge_filter.SetFeatureAngle(new_angle)
            set_mode_msg(f'EDGE.ANGLE: {new_angle:.1f}')
            logger.info('Audio edge angle: %.1f', new_angle)
            plotter.render()
        elif renderer.mode in ('ISOLINE', 'WIREFRAME'):
            _dec_iso()

    def _toggle_backface() -> None:
        state = not getattr(plotter, '_is_backface', False)
        plotter._is_backface = state
        if renderer.body_actor is not None:
            if state:
                renderer.body_actor.VisibilityOn()
            else:
                renderer.body_actor.VisibilityOff()
        elif renderer.main_actor is not None:
            prop = renderer.main_actor.GetProperty()
            if state:
                prop.BackfaceCullingOn()
            else:
                prop.BackfaceCullingOff()
        plotter.render()
        set_mode_msg(f'BACKFACE: {"ON" if state else "OFF"}')
        logger.info('Backface culling: %s', state)

    def _toggle_grid_bbox() -> None:
        visible = True
        if ctx.grid_actor is not None:
            visible = not bool(ctx.grid_actor.GetVisibility())
            if visible:
                ctx.grid_actor.VisibilityOn()
            else:
                ctx.grid_actor.VisibilityOff()
        if renderer.bbox_actor is not None:
            if visible:
                renderer.bbox_actor.VisibilityOn()
            else:
                renderer.bbox_actor.VisibilityOff()
        plotter.render()
        state = 'ON' if visible else 'OFF'
        set_mode_msg(f'GRID.BBOX: {state}')
        logger.info('Grid+BBox visibility: %s', state)

    def _toggle_turntable() -> None:
        renderer._is_turntable = not renderer._is_turntable
        set_mode_msg(
            f'TURNTABLE: '
            f'{"ON" if renderer._is_turntable else "OFF"}'
        )

    def _toggle_overlay() -> None:
        toggle_info_overlay(plotter)
        visible = plotter._is_overlay_visible
        if renderer.bbox_actor is not None:
            if visible:
                prev = getattr(plotter, '_overlay_prev_vis', {})
                if prev.get('_bbox_actor', True):
                    renderer.bbox_actor.VisibilityOn()
            else:
                renderer.bbox_actor.VisibilityOff()

    def _force_exit() -> None:
        renderer.keep_running = False
        if ctx.monitor_ctx[0] is not None:
            ctx.monitor_ctx[0].set()
            ctx.monitor_ctx[1].join(timeout=2.0)
        sysinfo_stop = getattr(plotter, '_sysinfo_stop', None)
        if sysinfo_stop is not None:
            sysinfo_stop.set()
        if ctx.executor is not None:
            logger.info(
                'Finalizing audio recording: %s', ctx.record_dir
            )
            ctx.executor.shutdown(wait=True)
        log_path = os.path.join(
            LOG_DIR, f'{ctx.base_name}.log'
        )
        log_session_end(
            ctx.base_name, ctx.total_frames, ctx.start_time,
            ctx.save_counter, ctx.record_dir,
        )
        logging.shutdown()
        Msg.Result(
            f'Audio playback for "{ctx.base_name}" finished.'
            f' ({ctx.total_frames} Frames)',
            divide=False,
        )
        if ctx.record_dir and ctx.save_counter > 0:
            Msg.Dim(
                f'Saved {ctx.save_counter} captured images'
                f' to "{os.path.relpath(ctx.record_dir)}".'
            )
        Msg.Dim(
            f'Please refer to the log file for details.'
            f' ({log_path})'
        )
        try:
            plotter.close()
        finally:
            os._exit(0)

    _UNSUPPORTED = {
        KEY_VTX: 'VERTEX.LABEL',
        KEY_NORMAL_COLOR: 'NORMAL.COLOR',
    }

    def _make_unsupported(mode_name: str):
        def _cb():
            msg = (
                f'[Error] Not supported "{mode_name}"'
                f' in AUDIO mode.'
            )
            logger.error(msg)
            plotter._error_msg = msg.upper()
            plotter._error_msg_time = time.time()
        return _cb

    def _apply_lighting_for_mode(mode: str) -> None:
        plotter._is_lighting = False
        apply_lighting(plotter)
        if mode == 'DEPTH':
            plotter._cmap_title = (
                f'DEPTH.{AXIS_NAMES[renderer._depth_axis]}'
            )
        elif mode == 'QUALITY':
            plotter._cmap_title = 'QUALITY'

    def _reset_audio_mode() -> None:

        renderer._iso_axis = AUDIO_ISO_AXIS
        renderer._color_axis = AUDIO_COLOR_AXIS
        renderer._iso_count = AUDIO_ISO_COUNT_DEFAULT
        renderer._depth_axis = AXIS_NAMES.index('CAM')
        renderer._edge_feature_angle = AUDIO_EDGE_FEATURE_ANGLE
        if renderer._edge_filter is not None:
            renderer._edge_filter.SetFeatureAngle(
                AUDIO_EDGE_FEATURE_ANGLE
            )
        renderer._is_turntable = True

        renderer.switch_mode(STARTUP_AUDIO_MODE)

        if getattr(plotter, '_is_smooth_shading', False):
            renderer.toggle_smooth_shading()

        plotter._cmap_lut = renderer._lut
        plotter._is_backface = DEFAULT_BACKFACE
        plotter._is_colorbar = DEFAULT_COLORBAR
        _apply_lighting_for_mode(STARTUP_AUDIO_MODE)

        ctx.tab_state = 0
        if ctx.grid_actor is not None:
            ctx.grid_actor.SetVisibility(True)
        if renderer.bbox_actor is not None:
            renderer.bbox_actor.SetVisibility(True)
        if renderer.body_actor is not None:
            renderer.body_actor.SetVisibility(DEFAULT_BACKFACE)
        set_mode_msg('RESET')
        logger.info('Audio mode full reset to defaults')
        plotter.render()

    def _switch_audio_mode(new_mode: str) -> None:
        if renderer.mode == new_mode:
            _reset_audio_mode()
            return
        renderer.switch_mode(new_mode)
        plotter._cmap_lut = renderer._lut
        plotter._is_backface = DEFAULT_BACKFACE
        plotter._is_colorbar = DEFAULT_COLORBAR
        _apply_lighting_for_mode(new_mode)
        set_mode_msg(new_mode)
        logger.info('Audio mode switched: %s', new_mode)
        plotter.render()

    def _tab_cycle() -> None:
        state = (ctx.tab_state + 1) % 3
        ctx.tab_state = state
        grid_on = (state == 0)
        body_on = (
            (state < 2) and getattr(plotter, '_is_backface', True)
        )
        if ctx.grid_actor is not None:
            ctx.grid_actor.SetVisibility(grid_on)
        if renderer.bbox_actor is not None:
            renderer.bbox_actor.SetVisibility(grid_on)
        if renderer.body_actor is not None:
            renderer.body_actor.SetVisibility(body_on)
        labels = ('ALL.ON', 'NO.GRID', 'ACTOR.ONLY')
        set_mode_msg(f'ACTOR: {labels[state]}')
        logger.info('Actor cycle: %s', labels[state])
        plotter.render()

    def _seek_fwd() -> None:
        ctx.seek_delta += AUDIO_SEEK_STEP
        set_mode_msg(f'SEEK +{AUDIO_SEEK_STEP}f')

    def _seek_bwd() -> None:
        ctx.seek_delta -= AUDIO_SEEK_STEP
        set_mode_msg(f'SEEK -{AUDIO_SEEK_STEP}f')

    def _goto_first() -> None:
        ctx.seek_delta = -ctx.total_frames
        set_mode_msg('SEEK: FIRST')

    def _goto_last() -> None:
        ctx.seek_delta = ctx.total_frames
        set_mode_msg('SEEK: LAST')

    def _toggle_smooth_shading() -> None:
        smooth = renderer.toggle_smooth_shading()
        msg = f'SMOOTH.SHADING: {"ON" if smooth else "OFF"}'
        set_mode_msg(msg)
        logger.info(msg)
        plotter.render()

    def _toggle_lighting() -> None:
        plotter._is_lighting = not getattr(
            plotter, '_is_lighting', False
        )
        apply_lighting(plotter)
        state = 'ON' if plotter._is_lighting else 'OFF'
        set_mode_msg(f'LIGHTING: {state}')
        logger.info('Audio lighting: %s', state)
        plotter.render()

    def _toggle_play() -> None:
        ctx.paused = not ctx.paused
        state = 'PAUSED' if ctx.paused else 'PLAYING'
        set_mode_msg(state)
        logger.info('Playback state: %s', state)

    def _toggle_help() -> None:
        actor = getattr(plotter, '_help_actor', None)
        if actor is None:
            return
        if actor.GetVisibility():
            actor.VisibilityOff()
        else:
            actor.VisibilityOn()
        plotter.render()

    cam_keys = (
        KEY_CAM_RESET
        if isinstance(KEY_CAM_RESET, list)
        else [KEY_CAM_RESET]
    )
    for key in cam_keys:
        plotter.add_key_event(key, cam_cbs['reset'])

    plotter.add_key_event(KEY_TURNTABLE, _toggle_turntable)
    plotter.add_key_event(KEY_CAM_PROJ, cam_cbs['toggle_proj'])
    plotter.add_key_event(KEY_CENTER_VIEW, cam_cbs['center_view'])
    plotter.add_key_event(KEY_KP_ZOOM_IN, cam_cbs['zoom_in'])
    plotter.add_key_event(KEY_KP_ZOOM_OUT, cam_cbs['zoom_out'])
    plotter.add_key_event(KEY_KP_DOLLY_IN, cam_cbs['dolly_in'])
    plotter.add_key_event(KEY_KP_DOLLY_OUT, cam_cbs['dolly_out'])
    plotter.add_key_event(KEY_ROT_YL, cam_cbs['rot_yl'])
    plotter.add_key_event(KEY_ROT_YR, cam_cbs['rot_yr'])
    plotter.add_key_event(KEY_ROT_XD, cam_cbs['rot_xd'])
    plotter.add_key_event(KEY_ROT_XU, cam_cbs['rot_xu'])
    plotter.add_key_event(KEY_SCREENSHOT, _screenshot)
    plotter.add_key_event(KEY_OVERLAY, _toggle_overlay)
    plotter.add_key_event(KEY_BACKFACE, _toggle_backface)
    plotter.add_key_event(KEY_GRID, _toggle_grid_bbox)
    dispatch_key(
        plotter._special_key_dispatch, KEY_AXIS_NEXT, lambda: _cycle_axis(1)
    )
    dispatch_key(
        plotter._special_key_dispatch, KEY_AXIS_PREV, lambda: _cycle_axis(-1)
    )
    plotter.add_key_event(KEY_INC, _kp_inc)
    plotter.add_key_event(KEY_DEC, _kp_dec)
    plotter.add_key_event('Escape', _force_exit)

    for _key, _name in _UNSUPPORTED.items():
        _keys = _key if isinstance(_key, list) else [_key]
        for k in _keys:
            plotter.add_key_event(k, _make_unsupported(_name))

    plotter.add_key_event(KEY_MESH_DEFAULT, _reset_audio_mode)
    plotter.add_key_event(
        KEY_WIRE, lambda: _switch_audio_mode('WIREFRAME')
    )
    plotter.add_key_event(
        KEY_SMOOTH, lambda: _switch_audio_mode('MESH')
    )
    plotter.add_key_event(
        KEY_ISO, lambda: _switch_audio_mode('ISOLINE')
    )
    plotter.add_key_event(
        KEY_DEPTH, lambda: _switch_audio_mode('DEPTH')
    )
    plotter.add_key_event(
        KEY_EDGE, lambda: _switch_audio_mode('EDGE')
    )
    plotter.add_key_event(
        KEY_FACE_NORMAL, lambda: _switch_audio_mode('FACE_NORMAL')
    )
    plotter.add_key_event(
        KEY_MESH_QUALITY, lambda: _switch_audio_mode('QUALITY')
    )
    dispatch_key(plotter._special_key_dispatch, KEY_ACTOR_NEXT, _tab_cycle)
    plotter.add_key_event(KEY_STEP_FWD, _seek_fwd)
    plotter.add_key_event(KEY_STEP_BWD, _seek_bwd)

    dispatch_key(
        plotter._special_key_dispatch, KEY_FIRST_FRAME, _goto_first
    )
    dispatch_key(
        plotter._special_key_dispatch, KEY_LAST_FRAME, _goto_last
    )

    plotter.add_key_event(KEY_SMOOTH_SHADING, _toggle_smooth_shading)
    plotter.add_key_event(KEY_LIGHT, _toggle_lighting)
    register_cam_pan(plotter, plotter.render, set_mode_msg)
    plotter.add_key_event(KEY_PLAY, _toggle_play)
    plotter.add_key_event(KEY_HELP, _toggle_help)

    def _apply_view(direction, viewup, label):
        cam = plotter.renderer.GetActiveCamera()
        fp = np.array(cam.GetFocalPoint())
        dist = cam.GetDistance()
        cam.SetPosition(*(fp + np.array(direction) * dist))
        cam.SetViewUp(*viewup)
        plotter.renderer.ResetCamera()
        set_mode_msg(label)
        plotter.render()

    dispatch_key(
        plotter._special_key_dispatch, KEY_VIEW_FRONT,
        lambda: _apply_view((0, 0, 1), (0, 1, 0), LBL_VIEW_FRONT),
    )
    dispatch_key(
        plotter._special_key_dispatch, KEY_VIEW_BACK,
        lambda: _apply_view((0, 0, -1), (0, 1, 0), LBL_VIEW_BACK),
    )
    dispatch_key(
        plotter._special_key_dispatch, KEY_VIEW_SIDE_L,
        lambda: _apply_view((-1, 0, 0), (0, 1, 0), LBL_VIEW_SIDE_L),
    )
    dispatch_key(
        plotter._special_key_dispatch, KEY_VIEW_SIDE_R,
        lambda: _apply_view((1, 0, 0), (0, 1, 0), LBL_VIEW_SIDE_R),
    )
    dispatch_key(
        plotter._special_key_dispatch, KEY_VIEW_TOP,
        lambda: _apply_view((0, 1, 0), (0, 0, -1), LBL_VIEW_TOP),
    )
    dispatch_key(
        plotter._special_key_dispatch, KEY_VIEW_BOTTOM,
        lambda: _apply_view((0, -1, 0), (0, 0, 1), LBL_VIEW_BOTTOM),
    )
