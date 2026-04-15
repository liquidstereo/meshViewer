import os
import logging
import time

from process.init import init_vtk, log_session_start
from process.overlay import init_overlays
from process.audio.camera import setup_audio_cam, make_cam_callbacks
from process.audio.state import init_audio_state
from process.keys.audio import register_audio_keys
from process.audio.loop import run_audio_loop
from process.load import show_loading
from configs.colorize import Msg

logger = logging.getLogger(__name__)

def exec_audio_viewer(audio_path: str, args) -> None:

    from process.viewer import (
        create_audio_plotter, load_audio, build_audio_scene,
        init_audio_actors, setup_audio_window, show_audio_window,
    )

    record_dir = args.save
    if record_dir:
        os.makedirs(record_dir, exist_ok=True)
        logger.info('Audio record dir: %s', record_dir)

    init_vtk()

    plotter = create_audio_plotter(args)

    log_session_start([audio_path], args)
    start = float(args.frame_start)
    end = (
        float(args.frame_end) if args.frame_end is not None else None
    )
    mag_t, total_frames, hop_len, actual_sr, global_max = load_audio(
        audio_path, start, end
    )

    show_loading()

    renderer, x_grid, grid_actor = build_audio_scene(
        plotter, actual_sr, hop_len, global_max, args
    )

    init_audio_actors(plotter, renderer)

    ctx = init_audio_state(
        plotter, audio_path, renderer, args,
        total_frames, mag_t, x_grid, grid_actor,
    )

    setup_audio_cam(plotter)

    def _set_mode_msg(msg: str) -> None:
        plotter._mode_msg = msg
        plotter._mode_msg_time = time.time()

    cam_cbs = make_cam_callbacks(plotter, _set_mode_msg)

    register_audio_keys(plotter, renderer, ctx, cam_cbs, _set_mode_msg)

    setup_audio_window(plotter, renderer, cam_cbs)

    if grid_actor is not None:
        grid_actor.VisibilityOff()
    if renderer.bbox_actor is not None:
        renderer.bbox_actor.VisibilityOff()

    show_audio_window(plotter)

    cam_cbs['reset']()

    init_overlays(plotter)

    run_audio_loop(plotter, renderer, ctx)
