import os
import sys
import time
import math
import logging
import threading
from contextlib import ExitStack
from concurrent.futures import ThreadPoolExecutor

from configs.colorize import Msg
from configs.system_resources import get_system_info, get_gpu_info
from configs.settings import (
    TARGET_ANIM_FPS, MAX_FRAME_SKIP,
    UPDATE_INTERVAL, UPDATE_INTERVAL_PLAY,
    SAVE_ALPHA, SAVE_PBO_ENABLED, SAVE_ENCODE_WORKERS,
    TURNTABLE_STEP,
)
import traceback

from process.apply_mode import apply_visual_mode, _active_mode_name
from process.mode.default import apply_default_reset
from process.mode.surface import apply_normal
from process.scene.grid import update_grid_bounds
from process.load.frame_integrity import format_broken_message
from process.window.display import capture_frame, PBOCapture
from process.render.save_sink import create_sink, format_saved_message
from process.render.headless_ui import (
    headless_progress, start_sysinfo_monitor, stop_sysinfo_monitor,
)
from process.init.exit_summary import emit_exit_summary, finalize_logs
from process.init.shutdown import close_progress, graceful_shutdown
from process.overlay.hud_texts import (
    update_status_text, update_log_overlay,
    update_mode_text, update_colorbar,
    update_periodic_overlays,
)

logger = logging.getLogger(__name__)

_FRAME_INTERVAL = 1.0 / TARGET_ANIM_FPS
_PERF_LOG_INTERVAL = 10.0
_HEADLESS_PLAY_MSG = (
    'EXPORTING SEQUENCE... PLEASE WAIT... (PRESS "Ctrl + C" TO QUIT)'
)

def _is_cam_dependent_mode(p) -> bool:
    return (
        getattr(p, '_is_vtx', False)
        or getattr(p, '_is_outline', False)
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

def _update_seq(plotter, idx):
    seq = getattr(plotter, '_seq_overlay', None)
    if seq is not None:
        seq.update(idx)

def _store_frame(sink, plotter, img, total, t_cap, t_sub) -> int:
    target = sink.submit(img)
    plotter._save_counter = sink.count
    logger.info(
        'SAVE_FRAME [%d/%d] cap=%.4fs sub=%.4fs out=%s',
        sink.count, total, t_cap, t_sub, os.path.basename(target),
    )
    return sink.count

def _finish_save(sink, count) -> None:
    sink.close()
    logger.info(
        'Save complete: %d frames -> %s', count, sink.target,
    )

def _mark_batch_complete(plotter, sink, count, bar) -> None:
    if bar is not None:
        title = getattr(plotter, '_batch_title', '') or ''
        bar.title = f'{title} COMPLETE'
    targets = getattr(plotter, '_batch_targets', None)
    if targets is not None and sink.display_target:
        targets.append(sink.display_target)
    plotter._batch_saved_count = count

def _start_playing_monitor(plotter, headless: bool) -> tuple:
    stop_event = threading.Event()
    thread = threading.Thread(
        target=_playing_monitor,
        args=(stop_event, _HEADLESS_PLAY_MSG if headless else None),
        daemon=True,
    )
    thread.start()
    plotter._blink_stop_event = stop_event
    plotter._blink_thread_ref = thread
    return stop_event, thread

def _on_save_complete(plotter, sink, count, bar, batch, headless) -> tuple:
    _finish_save(sink, count)
    if batch:
        _mark_batch_complete(plotter, sink, count, bar)
        return None, None
    if headless:
        return None, None
    close_progress(plotter)
    Msg.Dim(format_saved_message(count, sink.display_target))
    return _start_playing_monitor(plotter, headless)

def _emit_headless_exit(plotter, total, sink) -> None:

    graceful_shutdown(plotter, 'headless')
    input_name = getattr(plotter, '_input_name', '?')
    finalize_logs(
        input_name, total,
        getattr(plotter, '_start_time', None),
        sink.count, sink.display_target,
    )
    emit_exit_summary(
        input_name, total, sink.count, sink.display_target,
        headless=True,
    )

def render_loop(plotter, buffer) -> None:
    frame_count, fps_time = 0, time.time()
    _first_frame_logged = False
    ui_time = last_update_time = last_cam_check_time = 0.0
    last_anim_time = 0.0
    total = buffer.total
    t_get = t_mode = t_ui = t_render = 0.0
    save_path = getattr(plotter, '_save_path', None)
    save_loop = getattr(plotter, '_save_loop', False)
    headless = getattr(plotter, '_headless', False)
    batch = getattr(plotter, '_batch_active', False)
    batch_last = getattr(plotter, '_batch_last', True)

    gui_save = not headless and not batch
    batch_cycle_done = False
    save_counter = 0
    _RECORD_TOTAL = total
    rendered_idx = -1
    _prev_playing = False
    _blink_stop = None
    _blink_thread = None
    executor = ThreadPoolExecutor(max_workers=SAVE_ENCODE_WORKERS)
    save_sink = create_sink(plotter, save_path, executor) if save_path else None
    plotter._save_sink = save_sink
    pbo_capture = None
    if save_path and SAVE_PBO_ENABLED and headless:

        logger.info(
            'headless: PBO capture disabled'
            ' - using synchronous capture_frame()',
        )
    if save_path and SAVE_PBO_ENABLED and not headless:
        _w, _h = plotter.render_window.GetSize()
        _n_comp = 4 if SAVE_ALPHA else 3
        pbo_capture = PBOCapture(plotter.render_window, _w, _h, _n_comp)
        logger.info(
            'PBO capture enabled: %dx%d n_comp=%d',
            _w, _h, _n_comp,
        )

    _perf_n = 0
    _perf_get_sum = _perf_mode_sum = _perf_render_sum = 0.0
    _perf_last_log = time.perf_counter()

    logger.info('render_loop start: total_frames=%d', total)
    _loop_start = time.perf_counter()

    _stack = ExitStack()
    bar = None
    _bar_stop = _bar_thread = None
    if save_sink is not None:

        _bar_title = getattr(plotter, '_batch_title', None)
        bar = _stack.enter_context(
            headless_progress(_RECORD_TOTAL, _bar_title)
            if _bar_title else headless_progress(_RECORD_TOTAL)
        )
        _bar_stop, _bar_thread = start_sysinfo_monitor(bar)
    else:
        Msg.Dim(f'Load System Usage... Please Wait...', flush=True)

    def _close_bar():
        stop_sysinfo_monitor(_bar_stop, _bar_thread)
        _stack.close()

    plotter._progress_close = _close_bar

    last_anim_time = time.time() - _FRAME_INTERVAL
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
                if getattr(plotter, '_n_faces', 1) == 0:
                    from process.apply_mode import sync_pt_size_uniforms
                    sync_pt_size_uniforms(plotter)

        anim_fired = False
        skip = 0

        if plotter._is_playing and (
            save_path is not None
            or curr - last_anim_time >= _FRAME_INTERVAL
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
            cam.Azimuth(TURNTABLE_STEP * (skip + 1))
            plotter.renderer.ResetCameraClippingRange()
            needs_render = True

        if style_needed or anim_fired:
            t0 = time.perf_counter()
            mesh, tex = buffer.get(plotter._idx)
            t_get = time.perf_counter() - t0
            _broken = buffer.broken_source(plotter._idx)
            if _broken:
                plotter._error_msg = format_broken_message(_broken)
                plotter._error_msg_time = curr
            t0 = time.perf_counter()
            if not _first_frame_logged and style_needed:
                logger.info(
                    'first_render: apply_visual_mode start'
                    ' idx=%d', plotter._idx,
                )
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
                _ctx = (
                    'point clouds'
                    if getattr(plotter, '_n_faces', -1) == 0
                    else 'this mesh'
                )
                _msg = (
                    f'[Error] Not supported "{_mode}" '
                    f'for {_ctx} ({_detail}). '
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
            if not _first_frame_logged and style_needed:
                logger.info(
                    'first_render: apply_visual_mode done',
                )
            t_mode = time.perf_counter() - t0
            update_grid_bounds(plotter, _mesh_bounds(plotter, mesh))
            rendered_idx = plotter._idx
            buffer.notify(plotter._idx)
            if anim_fired:
                plotter._idx = (plotter._idx + 1) % total

                if batch and save_sink is None and plotter._idx == 0:
                    batch_cycle_done = True
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
            if not _first_frame_logged:
                logger.info('first_render: plotter.render() start')
            plotter.render()
            if not _first_frame_logged:
                logger.info(
                    'first_render: plotter.render() done'
                    ' (%.3fs from loop start)',
                    time.perf_counter() - _loop_start,
                )
                _first_frame_logged = True
            t_render = time.perf_counter() - t0
            logger.debug(
                'RENDER_DONE get=%.4fs style=%.4fs '
                'ui=%.4fs render=%.4fs',
                t_get, t_mode, t_ui, t_render,
            )
            if anim_fired:
                _t_total = t_get + t_mode + t_render
                logger.debug(
                    'FRAME_PERF [%d] get=%.1fms'
                    ' mode=%.1fms render=%.1fms total=%.1fms',
                    rendered_idx,
                    t_get * 1000, t_mode * 1000,
                    t_render * 1000, _t_total * 1000,
                )
                _perf_n += 1
                _perf_get_sum += t_get
                _perf_mode_sum += t_mode
                _perf_render_sum += t_render
                _now_perf = time.perf_counter()
                if (
                    _now_perf - _perf_last_log >= _PERF_LOG_INTERVAL
                    and _perf_n > 0
                ):
                    logger.info(
                        'PERF avg (last %d anim frames):'
                        ' get=%.1fms mode=%.1fms'
                        ' render=%.1fms total=%.1fms',
                        _perf_n,
                        _perf_get_sum / _perf_n * 1000,
                        _perf_mode_sum / _perf_n * 1000,
                        _perf_render_sum / _perf_n * 1000,
                        (_perf_get_sum + _perf_mode_sum
                         + _perf_render_sum) / _perf_n * 1000,
                    )
                    _perf_n = 0
                    _perf_get_sum = _perf_mode_sum = _perf_render_sum = 0.0
                    _perf_last_log = _now_perf
            if save_path and anim_fired:

                if pbo_capture is not None and pbo_capture.invalidated:
                    pbo_capture.destroy()
                    pbo_capture = None
                    _pbo_img = None
                if pbo_capture is not None:
                    _t_sub = time.perf_counter()
                    pbo_capture.submit()
                    _t_sub = time.perf_counter() - _t_sub
                    if _pbo_img is not None:
                        save_counter = _store_frame(
                            save_sink, plotter, _pbo_img,
                            _RECORD_TOTAL, _t_cap, _t_sub,
                        )
                        if bar is not None:
                            bar()
                        if not save_loop and save_counter >= _RECORD_TOTAL:

                            pbo_capture.destroy()
                            pbo_capture = None
                            save_path = None
                            plotter._save_path = None
                            _blink_stop, _blink_thread = _on_save_complete(
                                plotter, save_sink, save_counter,
                                bar, batch, headless,
                            )
                            if gui_save:
                                bar = None
                else:
                    _t_cap = time.perf_counter()
                    img = capture_frame(plotter)
                    _t_cap = time.perf_counter() - _t_cap
                    _t_sub = time.perf_counter()
                    save_counter = _store_frame(
                        save_sink, plotter, img,
                        _RECORD_TOTAL, _t_cap, 0.0,
                    )
                    _t_sub = time.perf_counter() - _t_sub
                    if bar is not None:
                        bar()
                    if not save_loop and save_counter >= _RECORD_TOTAL:
                        save_path = None
                        plotter._save_path = None
                        _blink_stop, _blink_thread = _on_save_complete(
                            plotter, save_sink, save_counter,
                            bar, batch, headless,
                        )
                        if gui_save:
                            bar = None

            if (headless or batch) and save_sink is not None and (
                save_path is None
            ):
                logger.info(
                    '%s: save finished (%d frames) - exiting loop',
                    'batch' if batch else 'headless', save_counter,
                )
                break

        if batch_cycle_done:
            logger.info('batch: playback cycle finished - exiting loop')
            break

        ui_interval = (
            UPDATE_INTERVAL_PLAY
            if plotter._is_playing
            else UPDATE_INTERVAL
        )
        if curr - last_update_time >= ui_interval:
            t0 = time.perf_counter()

            if not headless and plotter.iren is not None:
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

                if bar is None:
                    _blink_stop, _blink_thread = _start_playing_monitor(
                        plotter, headless,
                    )
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

        if save_path is not None and plotter._is_playing:

            time.sleep(0.0002)
        elif plotter._is_playing:
            _nxt = last_anim_time + _FRAME_INTERVAL
            _remain = _nxt - time.time() - 0.001
            if _remain > 0.002:
                time.sleep(_remain)
            else:
                time.sleep(0.0002)
        else:
            time.sleep(0.004)

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
    if save_sink is not None:
        save_sink.close()
    close_progress(plotter)
    logger.debug('render_loop ended')

    if headless and save_sink is not None and not batch:
        _emit_headless_exit(plotter, total, save_sink)
