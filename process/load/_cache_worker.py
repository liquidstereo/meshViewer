import os
import sys
import logging

os.environ.setdefault('OMP_NUM_THREADS', '1')

if __name__ == '__main__':
    logging.basicConfig(level=logging.ERROR, stream=sys.stderr)
    from process.load.loading_files import _build_single_npz
    _build_single_npz(sys.argv[1], sys.argv[2])
