import os
import time
import logging
from datetime import datetime

from configs.settings import (
    WINDOW_WIDTH, WINDOW_HEIGHT, TARGET_ANIM_FPS,
    STARTUP_AXIS,
    STARTUP_REVERSE_X_AXIS, STARTUP_REVERSE_Y_AXIS, STARTUP_REVERSE_Z_AXIS,
    FLIP_OBJECT_X, FLIP_OBJECT_Y, FLIP_OBJECT_Z,
)
from process.init.settings_log import (  # noqa: F401
    write_settings_log, write_output_settings_log,
)

from process.plotter.mode_settings import resolve_axis_settings

logger = logging.getLogger(__name__)

_NP_DATA_EXTS = ('.npy', '.npz')

def log_session_start(obj_files: list, args) -> None:
    ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
    level = 'DEBUG' if getattr(args, 'verbose', False) else 'INFO'
    log_msg = (
        f'MeshViewer Session Start - Input: "{args.input}", '
        f'Files: {len(obj_files)}, '
        f'Start Time: {ts}, '
        f'Window: {WINDOW_WIDTH}x{WINDOW_HEIGHT}, '
        f'fps: {TARGET_ANIM_FPS}, '
        f'Log Level: {level}'
    )
    if args.save:
        log_msg += f', Save Path: "{args.save}"'
    logger.info(log_msg)

    _ext = (
        os.path.splitext(obj_files[0])[1].lower() if obj_files else ''
    )
    _ftype = (
        'np_data' if _ext in _NP_DATA_EXTS
        else getattr(args, '_file_type', 'mesh')
    )
    (
        _axis, _rx, _ry, _rz, _fx, _fy, _fz,
    ) = resolve_axis_settings(_ftype)
    _rev_axes = [
        ax for ax, flag in (('X', _rx), ('Y', _ry), ('Z', _rz)) if flag
    ]
    _flip_axes = [
        ax for ax, flag in (('X', _fx), ('Y', _fy), ('Z', _fz)) if flag
    ]
    logger.info(
        'Startup Axis [%s]: AXIS_SWAP=%s, REVERSE=%s, FLIP_OBJECT=%s',
        _ftype,
        _axis,
        _rev_axes if _rev_axes else 'none',
        _flip_axes if _flip_axes else 'none',
    )

def log_session_end(
    input_name: str,
    total: int,
    start_t: float | None = None,
    save_counter: int = 0,
    save_path: str | None = None,
) -> None:
    import time
    if start_t:
        delta = time.time() - start_t
        h = int(delta // 3600)
        m = int((delta % 3600) // 60)
        s = delta % 60
        elapsed = f'{h:02d}:{m:02d}:{s:06.3f}'
    else:
        elapsed = '?'
    log_msg = (
        f'MeshViewer Session End - Input: "{input_name}", '
        f'Total: {total} frames, Elapsed Time: {elapsed}'
    )
    if save_path and save_counter > 0:
        log_msg += f', Saved: {save_counter} frames. ({save_path})'
    logger.info(log_msg)
