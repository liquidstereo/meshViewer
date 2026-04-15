import os
import sys
import time
import logging
import threading
from concurrent.futures import ThreadPoolExecutor
import numpy as np

from configs.colorize import Msg
from configs.system_resources import get_system_info, get_gpu_info
from configs.settings import (
    TARGET_ANIM_FPS, MAX_FRAME_SKIP,
    UPDATE_INTERVAL, UPDATE_INTERVAL_PLAY,
    SAVE_FILENAME_DIGITS, SAVE_FILENAME_EXT,
    SAVE_ALPHA, SAVE_PBO_ENABLED,
    TURNTABLE_STEP, WORKER_COUNT,
)
import traceback

from process.apply_mode import apply_visual_mode, _active_mode_name
from process.mode.default import apply_default_reset
from process.mode.surface import apply_normal
from process.scene.grid import update_grid_bounds
from process.window.display import capture_frame, save_frame_to_disk, PBOCapture
from process.overlay.hud_texts import (
    update_status_text, update_log_overlay,
    update_mode_text, update_colorbar,
    update_periodic_overlays,
)

logger = logging.getLogger(__name__)

_FRAME_INTERVAL = 1.0 / TARGET_ANIM_FPS

def _is_cam_dependent_mode(p) -> bool:
    return (
        getattr(p, '_is_vtx', False)
        or (getattr(p, '_n_faces', 1) == 0
            and getattr(p, '_pt_fog_enabled', False))
        or (getattr(p, '_is_depth', False)
            and getattr(p, '_depth_axis', 3) == 3)
        or (getattr(p, '_is_isoline', False)
            and getattr(p, '_iso_axis', 3) == 3)
        or (getattr(p, '_is_wire', False)
            and getattr(p, '_wire_axis', 3) == 3)
    )

def _playing_monitor(
    stop_event: threading.Event,
    play_msg: str = None,
) -> None:
    _PLAY_MSG = play_msg if play_msg is not None else (
        'PLAYING MESH FILE(s)... '
        '(PRESS "ESC" TO QUIT / "H" KEY FOR HELP)'
    )
    _gpu_avail = get_gpu_info() is not None

    _wait = Msg.Dim(
        'Load System Usage... Please Wait...', verbose=True,
    )
    sys.stdout.write(f'\033[2K\r{_wait}\n\033[?25l')
    sys.stdout.flush()

    blink_thread = threading.Thread(
        target=Msg.Blink,
        kwargs={
            'message': Msg.Dim(_PLAY_MSG, verbose=True),
            'stop_event': stop_event,
            'color': 'white',
            'interval': 0.5,
            'clear_on_finish': True,
            'upper': False,
        },
        daemon=True,
    )
    blink_thread.start()

    while not stop_event.is_set():
        info = get_system_info()
        gpu = get_gpu_info()
        if stop_event.is_set():
            break

        sys_info_str = Msg.Red(
            f'CPU: {info["cpu_percent"]:3.1f}% . ', verbose=True,
        )
        sys_info_str += Msg.Cyan(
            f'MEM: {info["memory_percent"]:3.1f}% . ', verbose=True,
        )
        if _gpu_avail:
            sys_info_str += Msg.Green(
                f'GPU: {gpu["gpu_percent"]:3.1f}% . ', verbose=True,
            )
            sys_info_str += Msg.Green(
                f'VRAM: {gpu["vram_percent"]:3.3f}%', verbose=True,
            )

        sys.stdout.write('\033[1A')
        Msg._clear_line()
        sys.stdout.write(f'{sys_info_str}\n')
        sys.stdout.flush()

    blink_thread.join(timeout=2.0)
    if blink_thread.is_alive():

        sys.stdout.write('\r\033[2K')

    sys.stdout.write('\033[1A')
    Msg._clear_line()
    sys.stdout.write('\033[?25h')
    sys.stdout.flush()

def _mesh_bounds(plotter, mesh) -> tuple:
    swap = getattr(plotter, '_axis_swap', 0)
    reverse = getattr(plotter, '_axis_reverse', (False, False, False))
    if swap != 0 or any(reverse):
        cache_key = (id(mesh), swap, reverse)
        if getattr(plotter, '_axis_swap_cache_key', None) == cache_key:
            mesh = plotter._axis_swap_cached_mesh
    b = mesh.bounds
    s = plotter._norm_scale
    cx, cy, cz = plotter._norm_center
    return (
        s * b[0] + (1 - s) * cx,
        s * b[1] + (1 - s) * cx,
        s * b[2] + (1 - s) * cy,
        s * b[3] + (1 - s) * cy,
        s * b[4] + (1 - s) * cz,
        s * b[5] + (1 - s) * cz,
    )

def _apply_pending_startup_cam(plotter) -> None:
    pending = getattr(plotter, '_pending_startup_cam', None)
    if pending is None:
        return
    direction, viewup = pending
    cx, cy, cz = plotter._norm_center
    fp = np.array([cx, cy, cz])
    init_pos = np.array(plotter._init_cam_pos[0])
    dist = float(np.linalg.norm(init_pos - fp))
    cam = plotter.renderer.GetActiveCamera()
    cam.SetPosition(*(fp + np.array(direction, dtype=float) * dist))
    cam.SetFocalPoint(*fp)
    cam.SetViewUp(*viewup)
    plotter.renderer.ResetCamera()
    plotter._init_cam_pos = plotter.camera_position
    plotter._init_parallel_scale = cam.GetParallelScale()
    plotter._init_view_angle = cam.GetViewAngle()
    plotter._pending_startup_cam = None

def _update_seq(plotter, idx):
    seq = getattr(plotter, '_seq_overlay', None)
    if seq is not None:
        seq.update(idx)

def render_loop(plotter, buffer) -> None:
    frame_count, fps_time = 0, time.time()
    ui_time = last_anim_time = last_update_time = last_cam_check_time = 0.0
    total = buffer.total
    t_get = t_mode = t_ui = t_render = 0.0
    save_path = getattr(plotter, '_save_path', None)
    save_loop = getattr(plotter, '_save_loop', False)
    save_stem = getattr(plotter, '_input_name', 'frame')
    save_counter = 0
    last_saved_idx = -1
    last_save_time = 0.0
    _single_continuous = save_loop and total == 1
    rendered_idx = -1
    _prev_playing = False
    _blink_stop = None
    _blink_thread = None
    executor = ThreadPoolExecutor(max_workers=WORKER_COUNT)
    pbo_capture = None
    _pbo_pending_fname = None
    if save_path and SAVE_PBO_ENABLED:
        _w, _h = plotter.render_window.GetSize()
        _n_comp = 4 if SAVE_ALPHA else 3
        plotter.render_window.SetMultiSamples(0)
        pbo_capture = PBOCapture(plotter.render_window, _w, _h, _n_comp)
        logger.info(
            'PBO capture enabled: %dx%d n_comp=%d msaa=0',
            _w, _h, _n_comp,
        )

    logger.debug('render_loop started: total_frames=%d', total)

    Msg.Dim(f'Load System Usage... Please Wait...', flush=True)

    while plotter.render_window is not None:
        curr = time.time()
        needs_render = False
        t_ui = 0.0

        if curr - fps_time > 0.5:
            elapsed = curr - fps_time
            plotter._fps = frame_count / elapsed
            frame_count = 0
            fps_time = curr
            needs_render = True

        style_needed = plotter._needs_update
        if style_needed:
            plotter._needs_update = False

        if (not style_needed
                and _is_cam_dependent_mode(plotter)
                and curr - last_cam_check_time >= UPDATE_INTERVAL):
            last_cam_check_time = curr
            cam = plotter.renderer.GetActiveCamera()
            cam_state = (
                cam.GetDirectionOfProjection(),
                cam.GetDistance(),
                cam.GetParallelScale(),
                cam.GetViewAngle(),
            )
            if cam_state != getattr(plotter, '_last_cam_state', None):
                plotter._last_cam_state = cam_state
                style_needed = True

        anim_fired = False
        skip = 0
        if plotter._is_playing and (
            curr - last_anim_time >= _FRAME_INTERVAL
        ):
            elapsed = curr - last_anim_time
            skip = 0 if save_path else min(
                int(elapsed / _FRAME_INTERVAL) - 1,
                MAX_FRAME_SKIP,
            )
            if skip > 0:
                plotter._idx = (plotter._idx + skip) % total
            last_anim_time = curr
            anim_fired = True

        if anim_fired and getattr(plotter, '_is_turntable', False):
            cam = plotter.renderer.GetActiveCamera()
            cam.Azimuth(TURNTABLE_STEP)
            plotter.renderer.ResetCameraClippingRange()
            needs_render = True

        if style_needed or anim_fired:
            t0 = time.perf_counter()
            mesh, tex = buffer.get(plotter._idx)
            t_get = time.perf_counter() - t0
            t0 = time.perf_counter()
            try:
                apply_visual_mode(plotter, mesh, tex)
                plotter._render_error = ''
            except Exception:
                _tb = traceback.format_exc()
                _lines = _tb.strip().splitlines()
                _raw = _lines[-1] if _lines else 'Unknown error'
                _detail = (
                    _raw.split(': ', 1)[-1]
                    if ': ' in _raw else _raw
                )
                _mode = _active_mode_name(plotter)
                _msg = (
                    f'[Error] Not supported "{_mode}" '
                    f'for point clouds ({_detail}). '
                    f'Reverting to default.'
                )
                logger.error(_msg)
                logger.error('Traceback (idx=%d):\n%s',
                             plotter._idx, _tb)
                plotter._render_error = _msg
                plotter._error_msg = _msg
                plotter._error_msg_time = curr
                try:
                    apply_default_reset(plotter)
                    apply_normal(plotter, mesh, None)
                except Exception:
                    logger.error(
                        'Fallback render failed:\n%s',
                        traceback.format_exc(),
                    )
                    if hasattr(plotter, '_mesh_actor'):
                        plotter._mesh_actor.VisibilityOn()
            t_mode = time.perf_counter() - t0
            update_grid_bounds(plotter, _mesh_bounds(plotter, mesh))
            if rendered_idx < 0:
                _apply_pending_startup_cam(plotter)
            rendered_idx = plotter._idx
            buffer.notify(plotter._idx)
            if anim_fired:
                plotter._idx = (plotter._idx + 1) % total
            frame_count += 1
            needs_render = True
            if style_needed:
                update_colorbar(plotter)
            logger.debug(
                'FRAME idx=%d anim=%s update=%s skip=%d '
                'get=%.4fs style=%.4fs',
                rendered_idx, anim_fired, style_needed,
                skip, t_get, t_mode,
            )

        if rendered_idx >= 0:
            if anim_fired:
                _update_seq(plotter, rendered_idx)
                needs_render = True
            elif style_needed:
                _update_seq(plotter, rendered_idx)

        if needs_render:
            update_status_text(
                plotter, rendered_idx,
                total, plotter._fps,
            )
            update_mode_text(plotter, curr)

        if needs_render and curr - ui_time > 0.5:
            update_periodic_overlays(plotter)
            ui_time = curr

        if needs_render:

            _pbo_img = None
            _t_cap = 0.0
            if pbo_capture is not None:
                t0 = time.perf_counter()
                _pbo_img = pbo_capture.retrieve()
                _t_cap = time.perf_counter() - t0

            t0 = time.perf_counter()
            plotter.render()
            t_render = time.perf_counter() - t0
            logger.debug(
                'RENDER_DONE get=%.4fs style=%.4fs '
                'ui=%.4fs render=%.4fs',
                t_get, t_mode, t_ui, t_render,
            )
            if (save_path
                    and (rendered_idx != last_saved_idx
                         or _single_continuous)
                    and curr - last_save_time >= _FRAME_INTERVAL):
                file_idx = (
                    save_counter if save_loop else rendered_idx
                )
                fname = os.path.join(
                    save_path,
                    f'{save_stem}'
                    f'.{file_idx:0{SAVE_FILENAME_DIGITS}d}'
                    f'.{SAVE_FILENAME_EXT}',
                )
                if pbo_capture is not None:
                    _t_sub = time.perf_counter()
                    pbo_capture.submit()
                    _t_sub = time.perf_counter() - _t_sub
                    if (_pbo_img is not None
                            and _pbo_pending_fname is not None):
                        executor.submit(
                            save_frame_to_disk,
                            _pbo_img, _pbo_pending_fname,
                        )
                        logger.info(
                            'SAVE_FRAME [%d/%d] fps=%.1f'
                            ' capture=%.4fs submit=%.4fs fname=%s',
                            save_counter, total, plotter._fps,
                            _t_cap, _t_sub,
                            os.path.basename(_pbo_pending_fname),
                        )
                    _pbo_pending_fname = fname
                else:
                    _t_cap = time.perf_counter()
                    img = capture_frame(plotter)
                    _t_cap = time.perf_counter() - _t_cap
                    _t_sub = time.perf_counter()
                    executor.submit(save_frame_to_disk, img, fname)
                    _t_sub = time.perf_counter() - _t_sub
                    logger.info(
                        'SAVE_FRAME [%d/%d] fps=%.1f'
                        ' capture=%.4fs submit=%.4fs fname=%s',
                        save_counter + 1, total, plotter._fps,
                        _t_cap, _t_sub, os.path.basename(fname),
                    )
                last_saved_idx = rendered_idx
                last_save_time = curr
                save_counter += 1
                plotter._save_counter = save_counter
                if last_saved_idx >= total - 1:
                    if save_loop:
                        logger.debug(
                            'Save loop cycle: %d total saved.',
                            save_counter,
                        )
                    else:
                        if (pbo_capture is not None
                                and _pbo_pending_fname is not None):
                            _final = pbo_capture.retrieve()
                            if _final is not None:
                                executor.submit(
                                    save_frame_to_disk,
                                    _final, _pbo_pending_fname,
                                )
                                logger.info(
                                    'SAVE_FRAME [%d/%d] fps=%.1f'
                                    ' capture=%.4fs submit=%.4fs'
                                    ' fname=%s',
                                    save_counter, total, plotter._fps,
                                    0.0, 0.0,
                                    os.path.basename(_pbo_pending_fname),
                                )
                            pbo_capture.destroy()
                            pbo_capture = None
                            _pbo_pending_fname = None
                        save_path = None
                        plotter._save_path = None
                        logger.info(
                            'Screenshot save complete: %d frames.',
                            save_counter,
                        )

        ui_interval = (
            UPDATE_INTERVAL_PLAY
            if plotter._is_playing
            else UPDATE_INTERVAL
        )
        if curr - last_update_time >= ui_interval:
            t0 = time.perf_counter()
            if plotter.iren is not None:
                plotter.iren.process_events()
            last_update_time = curr
            t_update = time.perf_counter() - t0
            if t_update > 0.05:
                logger.debug(
                    'SLOW_UPDATE took=%.4fs', t_update
                )

        is_playing = plotter._is_playing
        if is_playing != _prev_playing:
            rw = plotter.render_window
            if is_playing:
                rw.SetDesiredUpdateRate(TARGET_ANIM_FPS)
                _blink_stop = threading.Event()
                _blink_thread = threading.Thread(
                    target=_playing_monitor,
                    args=(_blink_stop,),
                    daemon=True,
                )
                _blink_thread.start()
                plotter._blink_stop_event = _blink_stop
                plotter._blink_thread_ref = _blink_thread
            else:
                rw.SetDesiredUpdateRate(0.001)
                if _blink_stop is not None:
                    _blink_stop.set()
                    _blink_thread.join(timeout=2.0)
                    _blink_stop = None
                    _blink_thread = None
                plotter._blink_stop_event = None
                plotter._blink_thread_ref = None
            _prev_playing = is_playing

        time.sleep(0.001)

    if _blink_stop is not None:
        _blink_stop.set()
        _blink_thread.join(timeout=2.0)
    sysinfo_stop = getattr(plotter, '_sysinfo_stop', None)
    if sysinfo_stop is not None:
        sysinfo_stop.set()
        plotter._sysinfo_thread.join(timeout=2.0)
    if pbo_capture is not None:
        pbo_capture.destroy()
    executor.shutdown(wait=True)
    logger.debug('render_loop ended')
