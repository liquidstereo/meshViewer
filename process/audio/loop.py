import os
import time
import threading
import logging
import numpy as np
from concurrent.futures import ThreadPoolExecutor

from configs.settings import (
    AUDIO_TARGET_FPS, TURNTABLE_STEP, WORKER_COUNT,
    AUDIO_MIN_DB_THRESHOLD, AUDIO_MIN_MESH_VALUE,
    SAVE_ENCODE_WORKERS, AUDIO_TARGET_FPS as _AUDIO_FPS,
)
from configs.colorize import Msg
from process.overlay.hud_texts import (
    update_status_text, update_mode_text,
    update_log_overlay, update_periodic_overlays,
)
from process.render.loop import _playing_monitor
from process.audio.state import AudioContext
from process.window.display import capture_frame
from process.render.save_sink import FrameSink, resolve_stem
from process.init.settings_log import write_output_settings_log

logger = logging.getLogger(__name__)

def run_audio_loop(
    plotter,
    renderer,
    ctx: AudioContext,
) -> None:
    Msg.Dim('Load System Usage... Please Wait...', flush=True)
    ctx.monitor_ctx[0] = threading.Event()
    ctx.monitor_ctx[1] = threading.Thread(
        target=_playing_monitor,
        args=(ctx.monitor_ctx[0],),
        kwargs={
            'play_msg': (
                'PLAYING AUDIO FILE... '
                '(PRESS "ESC" TO QUIT / "H" KEY FOR HELP)'
            ),
        },
        daemon=True,
    )
    ctx.monitor_ctx[1].start()

    plotter._blink_stop_event = ctx.monitor_ctx[0]
    plotter._blink_thread_ref = ctx.monitor_ctx[1]

    ctx.executor = (
        ThreadPoolExecutor(max_workers=SAVE_ENCODE_WORKERS)
        if ctx.is_recording else None
    )
    ctx.sink = None
    if ctx.is_recording:
        _w, _h = plotter.render_window.GetSize()
        ctx.sink = FrameSink(
            ctx.record_dir, resolve_stem(plotter),
            getattr(plotter, '_save_ext', 'png'),
            ctx.executor, _w, _h, _AUDIO_FPS,
            getattr(plotter, '_save_quality', 'high'),
        )
        write_output_settings_log(plotter, ctx.sink.settings_log_path)
        plotter._save_sink = ctx.sink
        logger.info(
            'Audio save sink: mode=%s target=%s fps=%d',
            'video' if ctx.sink.is_video else 'image_sequence',
            ctx.sink.target, _AUDIO_FPS,
        )
    frame_interval = 1.0 / AUDIO_TARGET_FPS
    azimuth_step = TURNTABLE_STEP / AUDIO_TARGET_FPS
    prev_t = time.perf_counter()
    ui_time = 0.0
    _cycle_done = False
    _grid_restored = False

    logger.debug(
        'render_loop started: total_frames=%d', ctx.total_frames
    )

    while renderer.keep_running and not plotter._closed:
        buf = np.zeros_like(ctx.x_grid, dtype=np.float32)
        i = 0
        while i < ctx.total_frames:
            if not renderer.keep_running or plotter._closed:
                break

            if ctx.seek_delta != 0:
                i = max(
                    0,
                    min(ctx.total_frames - 1, i + ctx.seek_delta),
                )
                buf = np.zeros_like(ctx.x_grid, dtype=np.float32)
                ctx.seek_delta = 0

            while (
                ctx.paused
                and renderer.keep_running
                and not plotter._closed
            ):
                if plotter.iren:
                    plotter.iren.process_events()
                update_mode_text(plotter, time.time())
                update_log_overlay(plotter)
                plotter.render()
                time.sleep(1.0 / 60)

            if not renderer.keep_running or plotter._closed:
                break

            now = time.perf_counter()
            dt = now - prev_t
            fps_val = 1.0 / dt if dt > 0 else 0.0
            prev_t = now

            frame_start_t = time.perf_counter()

            if plotter.iren:
                plotter.iren.process_events()

            _t0 = time.perf_counter()
            buf = np.roll(buf, 1, axis=0)
            row = ctx.mag_t[i, :].copy()
            row = np.maximum(0, row - AUDIO_MIN_DB_THRESHOLD)
            row[row < AUDIO_MIN_MESH_VALUE] = 0.0
            buf[0, :] = row
            _t_get = time.perf_counter() - _t0

            _t0 = time.perf_counter()
            if renderer._is_turntable:
                plotter.camera.Azimuth(azimuth_step)
            renderer.update(buf)
            _t_style = time.perf_counter() - _t0

            plotter._n_points = renderer.base_poly.n_points
            plotter._n_faces = renderer.base_poly.n_faces_strict

            if not _grid_restored:
                if ctx.grid_actor is not None:
                    ctx.grid_actor.VisibilityOn()
                if renderer.bbox_actor is not None:
                    renderer.bbox_actor.VisibilityOn()
                _grid_restored = True

            update_status_text(plotter, i, ctx.total_frames, fps_val)
            update_mode_text(plotter, time.time())

            if now - ui_time > 0.5:
                update_periodic_overlays(plotter)
                ui_time = now

            plotter.render()

            logger.debug(
                'FRAME idx=%d anim=True update=True skip=0 '
                'get=%.4fs style=%.4fs',
                i, _t_get, _t_style,
            )

            save_this = (
                ctx.is_recording
                and (ctx.continuous or not _cycle_done)
            )
            if save_this:

                ctx.sink.submit(capture_frame(plotter))
                ctx.save_counter = ctx.sink.count
                plotter._save_counter = ctx.save_counter
            else:
                elapsed = time.perf_counter() - frame_start_t
                wait = frame_interval - elapsed
                if wait > 0:
                    time.sleep(wait)

            i += 1

        _cycle_done = True

    if ctx.monitor_ctx[0] is not None:
        ctx.monitor_ctx[0].set()
        ctx.monitor_ctx[1].join(timeout=2.0)
    if ctx.executor is not None:
        logger.info(
            'Finalizing audio recording: %s', ctx.record_dir
        )
        ctx.executor.shutdown(wait=True)
        if ctx.sink is not None:
            ctx.sink.close()
            ctx.sink = None
            plotter._save_sink = None
