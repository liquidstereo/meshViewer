import logging

from configs.colorize import Msg
from configs.logging_cfg import (
    error_count, error_log_path, finalize_error_log,
    log_basename, log_file_path,
)
from process.init.session_log import log_session_end

logger = logging.getLogger(__name__)

_DIVIDER = '—'

_MSG_PLAYBACK = 'Mesh playback for "{name}" finished.{suffix}'
_MSG_CAPTURE = 'Frame capture completed for "{name}".{suffix}'
_MSG_ERROR = (
    '{count} Error Found. Please Refer To The'
    ' Log File For Details({path})'
)
_MSG_LOG = 'Please refer to the log file for details. ({path})'

def format_count_suffix(total: int) -> str:
    return f' ({total} Files)' if total > 1 else ''

def finalize_logs(input_name: str, total: int, start_t: float | None,
                  save_counter: int, save_path: str | None) -> None:
    log_session_end(input_name, total, start_t, save_counter, save_path)
    logging.shutdown()
    finalize_error_log(log_basename())

def emit_exit_summary(input_name: str, total: int, save_counter: int = 0,
                      sink_target: str | None = None,
                      headless: bool = False) -> None:
    template = _MSG_CAPTURE if headless else _MSG_PLAYBACK
    print(_DIVIDER)
    Msg.Result(
        template.format(
            name=input_name, suffix=format_count_suffix(total),
        ),
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
    Msg.Dim(_MSG_LOG.format(path=log_file_path()))
