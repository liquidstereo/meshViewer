import gc
import os
import sys
import ctypes
import logging

import psutil

logger = logging.getLogger(__name__)

_libc = None

def _get_libc():
    global _libc
    if _libc is None:
        try:
            _libc = ctypes.CDLL('libc.so.6')
        except OSError:
            _libc = False
    return _libc if _libc is not False else None

def _trim_heap() -> str:
    if sys.platform == 'linux':
        libc = _get_libc()
        if libc is not None:
            libc.malloc_trim(0)
            return 'gc+malloc_trim'
    elif sys.platform == 'win32':
        try:
            kernel32 = ctypes.windll.kernel32
            heap = kernel32.GetProcessHeap()
            kernel32.HeapCompact(heap, 0)
            return 'gc+HeapCompact'
        except (OSError, AttributeError):
            pass
    elif sys.platform == 'darwin':
        try:
            libsys = ctypes.CDLL('libSystem.dylib')
            libsys.malloc_zone_pressure_relief.argtypes = [
                ctypes.c_void_p, ctypes.c_size_t,
            ]
            libsys.malloc_zone_pressure_relief.restype = None
            libsys.malloc_zone_pressure_relief(None, 0)
            return 'gc+malloc_zone_pressure_relief'
        except (OSError, AttributeError):
            pass
    return 'gc'

def evict_file_cache(file_path: str) -> None:
    try:
        fd = os.open(file_path, os.O_RDONLY)
        os.posix_fadvise(fd, 0, 0, os.POSIX_FADV_DONTNEED)
        os.close(fd)
    except (AttributeError, OSError):
        pass

def release_process_memory(label: str = '') -> None:
    proc = psutil.Process()
    rss_before = proc.memory_info().rss
    vm_before = psutil.virtual_memory()

    gc.collect()
    method = _trim_heap()

    rss_after = proc.memory_info().rss
    vm_after = psutil.virtual_memory()

    _mb = 1024 ** 2
    freed_mb = (rss_before - rss_after) / _mb
    tag = f' [{label}]' if label else ''

    logger.info(
        'Memory release%s (%s):'
        ' RSS %.0f->%.0fMB (freed %.0fMB) |'
        ' SYS used %.0f->%.0fMB  avail %.0f->%.0fMB'
        '  (%.1f%%->%.1f%% of %.0fMB)',
        tag, method,
        rss_before / _mb, rss_after / _mb, freed_mb,
        vm_before.used / _mb, vm_after.used / _mb,
        vm_before.available / _mb, vm_after.available / _mb,
        vm_before.percent, vm_after.percent,
        vm_before.total / _mb,
    )
