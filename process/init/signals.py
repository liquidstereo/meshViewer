import os
import signal

import psutil

def register_sigint() -> None:
    def _handler(signum, frame):
        psutil.Process(os.getpid()).kill()
    signal.signal(signal.SIGINT, _handler)
