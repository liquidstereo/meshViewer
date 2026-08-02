import logging
import os
import signal

import psutil

from process.init.exit_summary import (
    emit_abort_summary, format_release_message,
)
from process.init.shutdown import graceful_shutdown, last_release_stats

logger = logging.getLogger(__name__)

_EXIT_INTERRUPT = 130
_LABEL_INTERRUPT = 'User Interrupted'
_UNKNOWN_TARGET = '?'

_target = {'plotter': None, 'buffer': None, 'input': None}
_interrupted = False
_summarized = False

def set_shutdown_target(plotter=None, buffer=None,
                        input_path: str | None = None) -> None:
    if plotter is not None:
        _target['plotter'] = plotter
    if buffer is not None:
        _target['buffer'] = buffer
    if input_path is not None:
        _target['input'] = input_path

def _resolve_plotter():
    plotter = _target['plotter']
    buffer = _target['buffer']
    if plotter is None:
        if buffer is not None:
            buffer.cleanup()
        return None
    if getattr(plotter, '_frame_buffer', None) is None:
        plotter._frame_buffer = buffer
    return plotter

def _emit_once(stats) -> None:
    global _summarized
    if _summarized:
        return
    _summarized = True
    emit_abort_summary(
        _LABEL_INTERRUPT,
        _target['input'] or _UNKNOWN_TARGET,
        os.getpid(),
        stats,
    )

def _on_interrupt() -> None:
    logger.warning('SIGINT received - running graceful shutdown.')
    graceful_shutdown(_resolve_plotter(), 'sigint')
    stats = last_release_stats()
    if stats is not None:

        logger.info('[SHUTDOWN] %s', format_release_message(stats))
    logging.shutdown()
    _emit_once(stats)
    os._exit(_EXIT_INTERRUPT)

def _force_kill() -> None:

    _emit_once(last_release_stats())
    psutil.Process(os.getpid()).kill()

def register_sigint() -> None:
    def _handler(signum, frame):
        global _interrupted
        if _interrupted:
            _force_kill()
        _interrupted = True
        _on_interrupt()
    signal.signal(signal.SIGINT, _handler)
