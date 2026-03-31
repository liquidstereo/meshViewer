import logging
from datetime import datetime

from configs.defaults import WINDOW_WIDTH, WINDOW_HEIGHT, TARGET_ANIM_FPS

logger = logging.getLogger(__name__)

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
