import os
import signal
import argparse
from logging import DEBUG, INFO

import psutil

from configs.settings import (
    INPUT_DIR_ROOT, OUTPUT_DIR_ROOT, MESH_DIR_ROOT, SEQUENCE_DIR_ROOT,
    SHOW_ANIMATION, DEFAULT_SMOOTH, DEFAULT_TEXTURE, DEFAULT_PRELOAD_ALL,
    SHOW_HIDE_INFO,
    MESH_EXTENSIONS,
    AUDIO_EXTENSIONS, AUDIO_DIR_ROOT, SCREENSHOT_SUBDIR,
)
from configs.logging_cfg import setup_logging
from configs.colorize import Msg
from process.viewer import (
    init_vtk, load_files, create_plotter,
    detect_file_type, apply_input_format,
    setup_cam, build_scene, register_keys,
    setup_window, show_window, load_seq_overlay,
    apply_hide_info, run_loop,
    exec_audio_viewer,
)
from process.plotter import init_plotter_state
from process.scene import init_actors
from process.overlay import init_overlays
from process.load import show_loading, detect_geometry_type
from process.init.session_log import write_settings_log

def parse_args():
    parser = argparse.ArgumentParser(description='Mesh Builder')
    parser.add_argument('-i',   '--input',   type=str, required=True)
    parser.add_argument('-img', '--images',  type=str, default=None)
    parser.add_argument('-s',   '--save',    type=str, nargs='?',
                        const='', default=None)
    parser.add_argument('-c',   '--continuous', action='store_true', default=False)
    parser.add_argument('--no-cache',           action='store_true', default=False)
    parser.add_argument('--hide-info',          action='store_true', default=SHOW_HIDE_INFO)
    parser.add_argument('-v',   '--verbose', action='store_true', default=False)
    parser.add_argument('-r',   '--range',   type=str, default=None,
                        metavar='START-END')
    args = parser.parse_args()

    _mesh_path       = os.path.join(MESH_DIR_ROOT,  args.input)
    _audio_path      = os.path.join(AUDIO_DIR_ROOT, args.input)
    _input_root_path = os.path.join(INPUT_DIR_ROOT, args.input)
    _input_exists = (
        os.path.isdir(_mesh_path) or os.path.isfile(_mesh_path)
        or os.path.isdir(args.input) or os.path.isfile(args.input)
        or os.path.isfile(_audio_path)
        or os.path.isfile(_input_root_path)
    )
    if not _input_exists:
        parser.error(f'Input not found: {args.input}')

    if args.images is None:
        args.images = os.path.join(SEQUENCE_DIR_ROOT, args.input)
    elif not os.path.isdir(args.images):
        parser.error(f'Images path not found: {args.images}')

    args.texture     = DEFAULT_TEXTURE
    args.animation   = SHOW_ANIMATION
    args.smooth      = DEFAULT_SMOOTH
    args.preload_all = DEFAULT_PRELOAD_ALL
    args.frame_start = 0
    args.frame_end   = None

    if args.range is not None:
        parts = args.range.split('-')
        try:
            if len(parts) != 2:
                raise ValueError
            s, e = float(parts[0]), float(parts[1])
        except ValueError:
            parser.error(
                '--range must be START-END '
                '(e.g., 0-1800 for frames, 0-30.5 for audio seconds)'
            )
        if s > e:
            parser.error('--range START must be <= END')
        args.frame_start, args.frame_end = s, e

    return args

def register_sigint():
    def _handler(signum, frame):
        psutil.Process(os.getpid()).kill()
    signal.signal(signal.SIGINT, _handler)

def exec_meshViewer(obj_files, args):
    init_vtk()
    buffer = load_files(obj_files, args)
    show_loading()
    plotter = create_plotter()
    args._file_type = detect_file_type(obj_files[0])
    init_plotter_state(plotter, args)
    apply_input_format(plotter, obj_files[0])
    setup_cam(plotter, buffer)
    build_scene(plotter)
    init_actors(plotter)
    register_keys(plotter, buffer.total)
    setup_window(plotter)
    show_window(plotter)
    init_overlays(plotter)
    apply_hide_info(plotter)
    load_seq_overlay(plotter, args, buffer.total)
    run_loop(plotter, buffer)

def main():
    register_sigint()
    args = parse_args()
    original_input = args.input

    _audio_in_input = os.path.join(INPUT_DIR_ROOT, args.input)
    _audio_in_root  = os.path.join(AUDIO_DIR_ROOT, args.input)
    _audio_path = None
    if (os.path.isfile(_audio_in_input)
            and _audio_in_input.lower().endswith(AUDIO_EXTENSIONS)):
        _audio_path = os.path.abspath(_audio_in_input)
    elif (os.path.isfile(_audio_in_root)
            and _audio_in_root.lower().endswith(AUDIO_EXTENSIONS)):
        _audio_path = os.path.abspath(_audio_in_root)
    elif (os.path.isfile(args.input)
            and args.input.lower().endswith(AUDIO_EXTENSIONS)):
        _audio_path = os.path.abspath(args.input)

    if _audio_path is not None:
        _base = os.path.splitext(os.path.basename(_audio_path))[0]
        args.input = _base
        if args.save == '':
            args.save = os.path.join(
                OUTPUT_DIR_ROOT, SCREENSHOT_SUBDIR, _base
            )
        setup_logging(_base, level=DEBUG if args.verbose else INFO)
        if args.save:
            write_settings_log(
                args.save, geo_type='audio',
                input_path=os.path.relpath(_audio_path),
            )
        exec_audio_viewer(_audio_path, args)
        return

    mesh_dir = os.path.join(MESH_DIR_ROOT, args.input)
    files = None

    if os.path.isdir(mesh_dir):

        src = mesh_dir
        args.input_path = os.path.relpath(src)
        files = sorted(
            os.path.join(src, f)
            for f in os.listdir(src)
            if f.lower().endswith(MESH_EXTENSIONS)
        )
    elif os.path.isfile(mesh_dir):

        file_path = os.path.abspath(mesh_dir)
        args.input_path = os.path.relpath(file_path)
        args.input = os.path.splitext(
            os.path.basename(file_path)
        )[0]
        files = [file_path]
    elif os.path.isdir(args.input):

        src = os.path.abspath(args.input)
        args.input_path = os.path.relpath(src)
        args.input = os.path.basename(src)
        files = sorted(
            os.path.join(src, f)
            for f in os.listdir(src)
            if f.lower().endswith(MESH_EXTENSIONS)
        )
    elif os.path.isfile(args.input):

        file_path = os.path.abspath(args.input)
        args.input_path = os.path.relpath(file_path)
        args.input = os.path.splitext(
            os.path.basename(file_path)
        )[0]
        files = [file_path]
    else:
        return

    if not files:
        Msg.Warning(f'No supported mesh files found: {original_input}')
        return

    if args.input != original_input:
        if args.images == os.path.join(
            SEQUENCE_DIR_ROOT, original_input
        ):
            args.images = os.path.join(
                SEQUENCE_DIR_ROOT, args.input
            )

    if args.save == '':
        args.save = os.path.join(OUTPUT_DIR_ROOT, args.input)

    setup_logging(args.input, level=DEBUG if args.verbose else INFO)
    if args.save:
        _geo = detect_file_type(files[0]) if files else 'mesh'
        write_settings_log(
            args.save, geo_type=_geo,
            input_path=getattr(args, 'input_path', ''),
        )

    _fs = int(args.frame_start)
    _fe = int(args.frame_end) if args.frame_end is not None else None
    if _fe is not None:
        files = files[_fs:_fe + 1]
    elif _fs > 0:
        files = files[_fs:]

    if files:
        exec_meshViewer(files, args)

if __name__ == '__main__':
    main()
