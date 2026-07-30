import os
import logging

import vtk as _vtk

from configs.settings import LOG_DIR, LOG_FORMAT, LOG_MSEC_FORMAT

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

ERROR_LOG_PREFIX = 'error_'

class _ErrorCounter(logging.Handler):

    def __init__(self):
        super().__init__(level=logging.ERROR)
        self.count = 0

    def emit(self, record):
        self.count += 1

_error_counter = _ErrorCounter()

def error_count() -> int:
    return _error_counter.count

class _ErrorFileHandler(logging.Handler):

    def __init__(self, path: str):
        super().__init__(level=logging.ERROR)
        self._path = path
        self._fp = open(path, 'w', encoding='utf-8')

    def emit(self, record):
        try:
            self._fp.write(self.format(record) + '\n')
            self._fp.flush()
        except (OSError, ValueError):
            pass

    def close(self):
        try:
            self._fp.close()
        except (OSError, ValueError):
            pass
        finally:
            super().close()

def make_error_handler(input_name: str) -> logging.Handler:
    path = error_log_path(input_name)
    if os.path.exists(path):
        os.remove(path)
    return _ErrorFileHandler(path)

def finalize_error_log(input_name: str) -> None:
    path = error_log_path(input_name)
    try:
        if os.path.exists(path) and os.path.getsize(path) == 0:
            os.remove(path)
    except OSError:
        pass

def error_log_path(input_name: str) -> str:
    return os.path.join(LOG_DIR, f'{ERROR_LOG_PREFIX}{input_name}.log')

def has_error_log(input_name: str) -> bool:
    path = error_log_path(input_name)
    return os.path.exists(path) and os.path.getsize(path) > 0

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

    err_handler = make_error_handler(input_name)
    err_handler.setFormatter(formatter)

    _error_counter.count = 0
    logging.basicConfig(
        level=logging.DEBUG,
        handlers=[handler, err_handler, _error_counter],
        force=True,
    )
    logging.getLogger('matplotlib').setLevel(logging.WARNING)

    vtk_log_path = os.path.join(LOG_DIR, f'{input_name}_vtk.log')
    vtk_win = _vtk.vtkFileOutputWindow()
    vtk_win.SetFileName(vtk_log_path)
    vtk_win.SetFlush(True)
    _vtk.vtkOutputWindow.SetInstance(vtk_win)

    import faulthandler
    _fault_fh = open(
        log_path, 'a', encoding='utf-8', buffering=1,
    )
    faulthandler.enable(file=_fault_fh)
