import logging
import sys

from configs.colorize import Msg
from configs.logging_cfg import (
    error_count, error_log_path, finalize_error_log,
    log_basename, log_file_path,
)
from process.init.session_log import log_session_end

logger = logging.getLogger(__name__)

_MSG_PLAYBACK = 'Mesh playback for "{name}" finished.{suffix}'
_MSG_CAPTURE = 'Frame capture completed for "{name}".{suffix}'
_MSG_ERROR = (
    '{count} Error Found. Please Refer To The'
    ' Log File For Details({path})'
)
_MSG_LOG = 'Please refer to the log file for details. ({path})'
_MSG_ABORT = '{label} ("{target}", pid: {pid} killed)'
_MSG_RELEASED = (
    'Memory released: RSS {before:.0f} -> {after:.0f}MB'
    ' (freed {freed:.0f}MB)'
)
_MB = 1024 ** 2

def print_divider() -> None:
    Msg.Divider()

def format_count_suffix(total: int) -> str:
    return f' ({total} Files)' if total > 1 else ''

def finalize_logs(input_name: str, total: int, start_t: float | None,
                  save_counter: int, save_path: str | None) -> None:
    log_session_end(input_name, total, start_t, save_counter, save_path)
    logging.shutdown()
    finalize_error_log(log_basename())

def emit_exit_summary(input_name: str, total: int, save_counter: int = 0,
                      sink_target: str | None = None,
                      headless: bool = False,
                      show_log_path: bool = True,
                      count_suffix: str | None = None) -> None:
    template = _MSG_CAPTURE if headless else _MSG_PLAYBACK
    suffix = (
        f' ({count_suffix})' if count_suffix
        else format_count_suffix(total)
    )
    print_divider()
    Msg.Result(
        template.format(name=input_name, suffix=suffix),
        divide=False,
    )
    err_count = error_count()
    if err_count > 0:
        Msg.Error(
            _MSG_ERROR.format(
                count=err_count, path=error_log_path(log_basename()),
            ),
            divide=False,
        )
    if sink_target and save_counter > 0:

        from process.render.save_sink import format_saved_message
        Msg.Dim(format_saved_message(save_counter, sink_target))
    if show_log_path:
        Msg.Dim(_MSG_LOG.format(path=log_file_path()))

def _clear_pending_line() -> None:
    if not sys.stdout.isatty():
        return
    sys.stdout.write('\r\033[2K\033[0J')
    sys.stdout.flush()

def format_release_message(stats: dict) -> str:
    return _MSG_RELEASED.format(
        before=stats['rss_before'] / _MB,
        after=stats['rss_after'] / _MB,
        freed=stats['freed'] / _MB,
    )

def emit_abort_summary(label: str, target: str, pid: int,
                       release: dict | None = None) -> None:

    _clear_pending_line()
    print_divider()
    Msg.Error(
        _MSG_ABORT.format(label=label, target=target, pid=pid),
        divide=False,
    )

    Msg.Dim(_MSG_LOG.format(path=log_file_path()))
