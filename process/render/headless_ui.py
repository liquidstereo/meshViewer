import sys
import shutil
import threading
import contextlib

from alive_progress import alive_bar

from configs.colorize import Msg
from configs.system_resources import get_system_info, get_gpu_info

_BAR_TITLE = 'EXPORTING FRAMES...'
_BAR_TITLE_LENGTH = 25
_BAR_LENGTH = 15
_JOIN_TIMEOUT = 2.0

_FALLBACK_COLS = 80

_COLOR_CPU = 'red'
_COLOR_MEM = 'cyan'
_COLOR_GPU = 'green'

def headless_progress(total: int, title: str = _BAR_TITLE):
    return _bar_context(total, title)

@contextlib.contextmanager
def _bar_context(total: int, title: str):
    with alive_bar(
        total, spinner=None,
        title=title,
        title_length=_BAR_TITLE_LENGTH, length=_BAR_LENGTH,
        dual_line=True, stats=True,
        elapsed=True, manual=False,
        enrich_print=False, force_tty=True,
    ) as bar:
        yield bar

    Msg.mark_dirty()

def text_cols() -> int:
    if not sys.stdout.isatty():
        return _FALLBACK_COLS
    return shutil.get_terminal_size(
        fallback=(_FALLBACK_COLS, 24)
    ).columns

def fit_sysinfo(styled: str, plain: str, cols: int) -> str:
    return styled if len(styled) <= cols else plain

def _sysinfo_parts() -> tuple:
    info = get_system_info()
    gpu = get_gpu_info()
    parts = [
        (_COLOR_CPU, f'CPU: {info["cpu_percent"]:3.1f}% . '),
        (_COLOR_MEM, f'MEM: {info["memory_percent"]:3.1f}%'),
    ]
    if gpu is not None:
        parts.append(
            (_COLOR_GPU, f' . GPU: {gpu["gpu_percent"]:3.1f}% . ')
        )
        parts.append(
            (_COLOR_GPU, f'VRAM: {gpu["vram_percent"]:3.3f}%')
        )
    return tuple(parts)

def format_sysinfo() -> str:
    parts = _sysinfo_parts()
    plain = ''.join(text for _, text in parts)
    return fit_sysinfo(Msg.Segments(parts), plain, text_cols())

def _sysinfo_worker(stop_event: threading.Event, bar) -> None:

    while not stop_event.is_set():
        text = format_sysinfo()
        if stop_event.is_set():
            break
        bar.text(text)

def start_sysinfo_monitor(bar) -> tuple:
    stop_event = threading.Event()
    thread = threading.Thread(
        target=_sysinfo_worker,
        args=(stop_event, bar),
        daemon=True,
    )
    thread.start()
    return stop_event, thread

def stop_sysinfo_monitor(stop_event, thread) -> None:
    if stop_event is None:
        return
    stop_event.set()
    if thread is not None:
        thread.join(timeout=_JOIN_TIMEOUT)
