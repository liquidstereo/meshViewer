import logging
import os

from configs.settings import OUTPUT_DIR_ROOT, SAVE_LIVE_PREFIX
from process.mode.labels import LBL_REC_CONSOLE
from process.window.title import set_recording_title

logger = logging.getLogger(__name__)

def request_toggle(p) -> None:
    if getattr(p, '_save_path', None) is not None:
        logger.info('Ctrl+R ignored: a -s save is already running')
        return
    p._rec_toggle_request = True

def resolve_record_dir(p) -> str:
    name = f"{SAVE_LIVE_PREFIX}{getattr(p, '_input_name', 'frame')}"
    saved = getattr(p, '_save_dir', None)
    if saved:
        return os.path.join(os.path.dirname(saved) or '.', name)
    return os.path.join(OUTPUT_DIR_ROOT, name)

def start(p, executor):
    from process.render.save_sink import create_sink
    p._save_prefix = SAVE_LIVE_PREFIX
    sink = create_sink(p, resolve_record_dir(p), executor)
    p._rec_sink = sink
    p._save_sink = sink
    set_recording_title(p, True)
    logger.info('Live recording started -> %s', sink.target)
    return sink

def stop(p, sink) -> int:
    count = sink.count
    sink.close()
    p._save_prefix = ''
    set_recording_title(p, False)
    p._rec_sink = None
    logger.info(
        'Live recording stopped: %d frames -> %s', count, sink.target,
    )
    return count

def console_message() -> str:
    return LBL_REC_CONSOLE
