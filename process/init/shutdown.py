import logging

from process.load.memory_guard import release_process_memory

logger = logging.getLogger(__name__)

_LOG_ENTER = '[SHUTDOWN] reason=%s'
_LOG_STEP = '[SHUTDOWN] %s'
_LOG_FAIL = '[SHUTDOWN] step "%s" failed'
_JOIN_TIMEOUT = 2.0
_MONITOR_THREADS = (
    ('_blink_stop_event', '_blink_thread_ref'),
    ('_sysinfo_stop', '_sysinfo_thread'),
)

_started = False
_release_stats = None

def close_progress(plotter) -> None:
    fn = getattr(plotter, '_progress_close', None)
    if fn is None:
        return
    plotter._progress_close = None
    fn()

def _close_save_sink(plotter) -> None:
    sink = getattr(plotter, '_save_sink', None)
    if sink is None:
        return

    sink.close()
    logger.info(_LOG_STEP, 'save sink closed')

def _stop_monitor_threads(plotter) -> None:
    for stop_attr, thread_attr in _MONITOR_THREADS:
        event = getattr(plotter, stop_attr, None)
        if event is not None:
            event.set()
        thread = getattr(plotter, thread_attr, None)
        if thread is not None and thread.is_alive():
            thread.join(timeout=_JOIN_TIMEOUT)
    close_progress(plotter)
    logger.info(_LOG_STEP, 'monitor threads stopped')

def _release_frame_buffer(plotter) -> None:
    buffer = getattr(plotter, '_frame_buffer', None)
    if buffer is None:
        return
    buffer.cleanup()
    plotter._frame_buffer = None

def _teardown_vtk(plotter) -> None:
    renderer = getattr(plotter, 'renderer', None)
    if renderer is not None:
        renderer.RemoveAllViewProps()
    plotter.close()
    logger.info(_LOG_STEP, 'VTK teardown done')

def _run_step(name: str, step, plotter) -> None:
    if plotter is None:
        return
    try:
        step(plotter)
    except Exception:

        logger.error(_LOG_FAIL, name, exc_info=True)

def graceful_shutdown(plotter, reason: str) -> None:
    global _started, _release_stats
    if _started:
        return
    _started = True
    logger.info(_LOG_ENTER, reason)
    _run_step('save_sink', _close_save_sink, plotter)
    _run_step('monitor_threads', _stop_monitor_threads, plotter)
    _run_step('frame_buffer', _release_frame_buffer, plotter)
    _run_step('vtk_teardown', _teardown_vtk, plotter)
    _release_stats = release_process_memory('shutdown')

def is_shutdown_started() -> bool:
    return _started

def last_release_stats() -> dict | None:
    return _release_stats
