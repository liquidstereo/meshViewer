import argparse

from configs.settings import (
    SHOW_HIDE_INFO,
    SAVE_EXT, SAVE_QUALITY, SAVE_QUALITY_PRESETS,
)
from process.init.signals import register_sigint
from process.init.cli_args import validate_args
from process.init.input_resolve import (
    resolve_audio_input, resolve_mesh_files, slice_frame_range,
    prepare_session,
)
from process.viewer import (
    init_vtk, load_files, create_plotter,
    detect_input_type, apply_input_format,
    setup_cam, build_scene, register_keys,
    setup_window, pre_warm_first_frame, show_window,
    load_seq_overlay, apply_hide_info, run_loop,
    exec_audio_viewer,
)
from process.plotter import init_plotter_state
from process.scene import init_actors
from process.overlay import init_overlays
from process.load import show_loading

def parse_args():
    parser = argparse.ArgumentParser(description='Mesh Builder')
    parser.add_argument('-i',   '--input',   type=str, required=True)
    parser.add_argument('-img', '--images',  type=str, default=None)
    parser.add_argument('-s',   '--save',    type=str, nargs='?',
                        const='', default=None)
    parser.add_argument('-f',   '--format',  type=str, default=SAVE_EXT,
                        metavar='EXT')
    parser.add_argument('-q',   '--quality', type=str, default=SAVE_QUALITY,
                        choices=tuple(SAVE_QUALITY_PRESETS),
                        metavar='QUALITY')
    parser.add_argument('-m',   '--mode',    type=str, default=None,
                        metavar='MODE')
    parser.add_argument('-c',   '--continuous', action='store_true', default=False)
    parser.add_argument('--no-cache',           action='store_true', default=False)
    parser.add_argument('--no-normal',          action='store_true', default=False)
    parser.add_argument('--preload-all',        action='store_true', default=False)
    parser.add_argument('--hide-info',          action='store_true', default=SHOW_HIDE_INFO)
    parser.add_argument('--headless',           action='store_true', default=False)
    parser.add_argument('-v',   '--verbose', action='store_true', default=False)
    parser.add_argument('-r',   '--range',   type=str, default=None,
                        metavar='START-END')
    args = parser.parse_args()
    validate_args(parser, args)
    return args

def exec_meshViewer(obj_files, args):
    init_vtk()
    buffer = load_files(obj_files, args)
    show_loading()
    plotter = create_plotter(args.headless)
    detect_input_type(args, obj_files[0])
    init_plotter_state(plotter, args)
    apply_input_format(plotter, obj_files[0])
    setup_cam(plotter, buffer)
    build_scene(plotter)
    init_actors(plotter)
    register_keys(plotter, buffer.total)
    setup_window(plotter)
    pre_warm_first_frame(plotter, buffer)
    show_window(plotter, args.headless)
    init_overlays(plotter)
    apply_hide_info(plotter)
    load_seq_overlay(plotter, args, buffer.total)
    run_loop(plotter, buffer)

def main():
    register_sigint()
    args = parse_args()
    audio_path = resolve_audio_input(args)
    if audio_path is not None:
        prepare_session(args, None, geo_type='audio')
        exec_audio_viewer(audio_path, args)
        return

    obj_files = resolve_mesh_files(args)
    if not obj_files:
        return

    prepare_session(args, obj_files)
    obj_files = slice_frame_range(obj_files, args)
    if obj_files:
        exec_meshViewer(obj_files, args)

if __name__ == '__main__':
    main()
