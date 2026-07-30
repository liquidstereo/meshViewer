import os
import sys
import signal
import logging

os.environ.setdefault('OMP_NUM_THREADS', '1')

_FILE_TIMEOUT = 60

DONE_PREFIX = 'DONE '
ERROR_PREFIX = 'ERROR '
TIMEOUT_PREFIX = 'TIMEOUT '

LINE_DONE = 'done'
LINE_ERROR = 'error'
LINE_OTHER = ''

def classify_line(line: str) -> str:
    if line.startswith(DONE_PREFIX):
        return LINE_DONE
    if line.startswith((ERROR_PREFIX, TIMEOUT_PREFIX)):
        return LINE_ERROR
    return LINE_OTHER

class _Timeout(Exception):
    pass

def _alarm_handler(signum, frame):
    raise _Timeout()

if __name__ == '__main__':
    logging.basicConfig(level=logging.ERROR, stream=sys.stderr)
    from process.load.loading_files import _build_single_npz

    npz_dir = sys.argv[1]
    obj_paths = sys.argv[2:]

    _has_sigalrm = hasattr(signal, 'SIGALRM')
    if _has_sigalrm:
        signal.signal(signal.SIGALRM, _alarm_handler)

    for obj_path in obj_paths:
        _name = os.path.basename(obj_path)
        try:
            if _has_sigalrm:
                signal.alarm(_FILE_TIMEOUT)
            _build_single_npz(obj_path, npz_dir)
        except _Timeout:
            print(
                f'{TIMEOUT_PREFIX}{_name}',
                file=sys.stderr, flush=True,
            )
        except Exception as e:
            print(
                f'{ERROR_PREFIX}{_name}: {e}',
                file=sys.stderr, flush=True,
            )
        finally:
            if _has_sigalrm:
                signal.alarm(0)
            print(f'{DONE_PREFIX}{_name}', flush=True)
