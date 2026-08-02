import os
from logging import DEBUG, INFO

from configs.settings import (
    INPUT_DIR_ROOT, OUTPUT_DIR_ROOT, MESH_DIR_ROOT, SEQUENCE_DIR_ROOT,
    MESH_EXTENSIONS, AUDIO_EXTENSIONS, AUDIO_DIR_ROOT, SCREENSHOT_SUBDIR,
)
from configs.logging_cfg import setup_logging
from configs.colorize import Msg
from process.viewer import detect_file_type

def resolve_audio_input(args) -> str | None:
    audio_path = _find_audio_path(args.input)
    if audio_path is None:
        return None
    base = os.path.splitext(os.path.basename(audio_path))[0]
    args.input = base
    args.input_path = os.path.relpath(audio_path)
    if args.save == '':
        args.save = os.path.join(OUTPUT_DIR_ROOT, SCREENSHOT_SUBDIR, base)
    return audio_path

def resolve_mesh_files(args) -> list:
    original_input = args.input
    files = _collect_mesh_files(args)
    if files is None:
        return []
    if not files:
        Msg.Warning(f'No supported mesh files found: {original_input}')
        return []
    _sync_derived_paths(args, original_input)
    return files

def slice_frame_range(files: list, args) -> list:

    start = int(args.frame_start)
    end = int(args.frame_end) if args.frame_end is not None else None
    if end is not None:
        return files[start:end + 1]
    if start > 0:
        return files[start:]
    return files

def prepare_session(args, files: list | None,
                    geo_type: str | None = None) -> None:
    setup_logging(
        args.input, level=DEBUG if args.verbose else INFO,
        headless=args.headless,
    )
    if geo_type is None:
        geo_type = detect_file_type(files[0]) if files else 'mesh'

    args._geo_type = geo_type

def _find_audio_path(name: str) -> str | None:
    candidates = (
        os.path.join(INPUT_DIR_ROOT, name),
        os.path.join(AUDIO_DIR_ROOT, name),
        name,
    )
    for path in candidates:
        if (os.path.isfile(path)
                and path.lower().endswith(AUDIO_EXTENSIONS)):
            return os.path.abspath(path)
    return None

def _collect_mesh_files(args) -> list | None:
    mesh_dir = os.path.join(MESH_DIR_ROOT, args.input)
    if os.path.isdir(mesh_dir):
        return _list_dir_files(args, mesh_dir)
    if os.path.isfile(mesh_dir):
        return _single_file(args, mesh_dir)
    if os.path.isdir(args.input):
        src = os.path.abspath(args.input)
        files = _list_dir_files(args, src)
        args.input = os.path.basename(src)
        return files
    if os.path.isfile(args.input):
        return _single_file(args, args.input)
    return None

def _list_dir_files(args, src: str) -> list:
    args.input_path = os.path.relpath(src)
    return sorted(
        os.path.join(src, f)
        for f in os.listdir(src)
        if f.lower().endswith(MESH_EXTENSIONS)
    )

def _single_file(args, path: str) -> list:
    file_path = os.path.abspath(path)
    args.input_path = os.path.relpath(file_path)
    args.input = os.path.splitext(os.path.basename(file_path))[0]
    return [file_path]

def _sync_derived_paths(args, original_input: str) -> None:

    if args.input != original_input:
        if args.images == os.path.join(SEQUENCE_DIR_ROOT, original_input):
            args.images = os.path.join(SEQUENCE_DIR_ROOT, args.input)

    if args.save == '':
        args.save = os.path.join(OUTPUT_DIR_ROOT, args.input)
