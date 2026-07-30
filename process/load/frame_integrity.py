import os
import logging

logger = logging.getLogger(__name__)

BUILD_FAILED_MARKER = 'build_failed.marker'

BROKEN_MSG_PREFIX = 'Broken source: '

def format_broken_message(name: str) -> str:
    return f'{BROKEN_MSG_PREFIX}{name}'

def broken_name_map(holds: dict, obj_files: list) -> dict:
    return {
        idx: os.path.basename(obj_files[idx])
        for idx in holds if idx < len(obj_files)
    }

def marker_path(frame_dir: str) -> str:
    return os.path.join(frame_dir, BUILD_FAILED_MARKER)

def write_build_marker(frame_dir: str, reason: str) -> None:
    try:
        with open(marker_path(frame_dir), 'w', encoding='utf-8') as f:
            f.write(reason)
    except OSError as e:
        logger.warning(
            'Build marker write failed [%s]: %s', frame_dir, e,
        )

def clear_build_marker(frame_dir: str) -> None:
    try:
        os.remove(marker_path(frame_dir))
    except OSError:
        pass

def is_build_failed(src_path: str, frame_dir: str) -> bool:
    m_path = marker_path(frame_dir)
    if not os.path.exists(m_path):
        return False
    try:
        return os.path.getmtime(src_path) <= os.path.getmtime(m_path)
    except OSError:
        return False

def split_broken_sources(obj_files: list, frame_dir_fn) -> tuple:
    kept, broken = [], []
    for path in obj_files:
        if os.path.exists(marker_path(frame_dir_fn(path))):
            broken.append(path)
        else:
            kept.append(path)
    return kept, broken

def log_broken_sources(broken: list, total: int) -> None:
    if not broken:
        return
    logger.error(
        'Broken source summary: %d of %d file(s) excluded from'
        ' playback (empty or truncated). Re-export them to restore.',
        len(broken), total,
    )
    for path in broken:
        logger.error('Broken source: %s', os.path.basename(path))

def log_invalid_frames(holds: dict, obj_files: list) -> None:
    if not holds:
        return
    logger.error(
        'Invalid frame summary: %d frame(s) could not be loaded'
        ' (empty or truncated source files).', len(holds),
    )
    for idx in sorted(holds):
        name = (
            os.path.basename(obj_files[idx])
            if idx < len(obj_files) else '?'
        )
        logger.error(
            'Invalid frame [idx=%d] %s -> held from idx=%d',
            idx, name, holds[idx],
        )

def plan_frame_holds(valid_flags: list) -> dict:
    holds = {}
    last_valid = None
    pending = []
    first_valid = None
    for idx, ok in enumerate(valid_flags):
        if ok:
            last_valid = idx
            if first_valid is None:
                first_valid = idx
            continue
        if last_valid is None:
            pending.append(idx)
            continue
        holds[idx] = last_valid
    if first_valid is None:
        return {}
    for idx in pending:
        holds[idx] = first_valid
    return holds
