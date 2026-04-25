import os
import logging

import vtk as _vtk

from configs.settings import LOG_DIR, LOG_FORMAT, LOG_MSEC_FORMAT

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

class _DetailFormatter(logging.Formatter):
    def format(self, record):
        if record.levelno >= logging.ERROR:
            try:
                rel = os.path.relpath(record.pathname, _PROJECT_ROOT)
            except ValueError:
                rel = record.pathname
            prefix = (
                f'@{rel}:{record.lineno}'
                f' | {record.funcName}(): '
            )
            orig_msg, orig_args = record.msg, record.args
            try:
                record.msg = prefix + record.getMessage()
                record.args = None
                return super().format(record)
            finally:
                record.msg, record.args = orig_msg, orig_args
        return super().format(record)

def setup_logging(
    input_name: str,
    level: int = logging.INFO,
) -> None:
    os.makedirs(LOG_DIR, exist_ok=True)
    log_path = os.path.join(LOG_DIR, f'{input_name}.log')

    handler = logging.FileHandler(log_path, mode='w', encoding='utf-8')
    handler.setLevel(level)
    formatter = _DetailFormatter(LOG_FORMAT)
    formatter.default_msec_format = LOG_MSEC_FORMAT
    handler.setFormatter(formatter)

    logging.basicConfig(level=logging.DEBUG, handlers=[handler], force=True)
    logging.getLogger('matplotlib').setLevel(logging.WARNING)

    vtk_log_path = os.path.join(LOG_DIR, f'{input_name}_vtk.log')
    vtk_win = _vtk.vtkFileOutputWindow()
    vtk_win.SetFileName(vtk_log_path)
    vtk_win.SetFlush(True)
    _vtk.vtkOutputWindow.SetInstance(vtk_win)
