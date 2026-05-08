import os
import sys
import signal
import logging

os.environ.setdefault('OMP_NUM_THREADS', '1')

_FILE_TIMEOUT = 60

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
        try:
            if _has_sigalrm:
                signal.alarm(_FILE_TIMEOUT)
            _build_single_npz(obj_path, npz_dir)
        except _Timeout:
            print(
                f'TIMEOUT {os.path.basename(obj_path)}',
                file=sys.stderr, flush=True,
            )
        except Exception as e:
            print(
                f'ERROR {os.path.basename(obj_path)}: {e}',
                file=sys.stderr, flush=True,
            )
        finally:
            if _has_sigalrm:
                signal.alarm(0)
