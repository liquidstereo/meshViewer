import os

from configs.settings import (
    INPUT_DIR_ROOT, MESH_DIR_ROOT, SEQUENCE_DIR_ROOT,
    SHOW_ANIMATION, DEFAULT_SMOOTH, DEFAULT_TEXTURE, DEFAULT_PRELOAD_ALL,
    AUDIO_DIR_ROOT,
    SAVE_VIDEO_EXTS, SAVE_IMAGE_EXTS,
)
from process.record import check_ffmpeg, is_video_ext, is_image_ext
from process.load.cache_policy import set_no_normal, set_startup_mode
from process.plotter.state import (
    MESH_STARTUP_MODES, PT_STARTUP_MODES, ALL_STARTUP_MODES,
)

def validate_args(parser, args) -> None:
    _check_input_exists(parser, args)
    _resolve_derived_paths(parser, args)
    _inject_defaults(args)
    _check_save_format(parser, args)
    _check_headless(parser, args)
    _check_mode(parser, args)
    _check_save_encoder(parser, args)
    _parse_range(parser, args)

def _check_input_exists(parser, args) -> None:
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

def _resolve_derived_paths(parser, args) -> None:

    if args.images is None:
        args.images = os.path.join(SEQUENCE_DIR_ROOT, args.input)
    elif not os.path.isdir(args.images):
        parser.error(f'Images path not found: {args.images}')

def _inject_defaults(args) -> None:
    args.texture     = DEFAULT_TEXTURE
    args.animation   = SHOW_ANIMATION
    args.smooth      = DEFAULT_SMOOTH
    args.preload_all = args.preload_all or DEFAULT_PRELOAD_ALL
    args.frame_start = 0
    args.frame_end   = None

def _check_save_format(parser, args) -> None:
    args.format = args.format.lower().lstrip('.')
    if not (is_video_ext(args.format) or is_image_ext(args.format)):
        parser.error(
            f'--format must be one of '
            f'{SAVE_VIDEO_EXTS + SAVE_IMAGE_EXTS}: {args.format}'
        )

def _check_headless(parser, args) -> None:

    if not args.headless:
        return
    if args.save is None:
        parser.error('--headless requires -s')
    if args.continuous:
        parser.error('--headless cannot be used with -c')
    args.animation = True

def _check_mode(parser, args) -> None:

    if args.mode is not None:
        args.mode = args.mode.strip().lower()
        if args.mode not in ALL_STARTUP_MODES:
            parser.error(
                f'--mode must be one of\n'
                f'  mesh       : {", ".join(sorted(MESH_STARTUP_MODES))}\n'
                f'  pointcloud : {", ".join(sorted(PT_STARTUP_MODES))}\n'
                f'got: {args.mode}'
            )

    set_startup_mode(args.mode)
    set_no_normal(args.no_normal)

def _check_save_encoder(parser, args) -> None:
    args.quality = args.quality.lower()
    if is_video_ext(args.format) and not check_ffmpeg():
        parser.error(
            f'ffmpeg not found - required for "{args.format}" output. '
            f'Use "-f png" for image sequence output.'
        )

def _parse_range(parser, args) -> None:

    if args.range is None:
        return
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
