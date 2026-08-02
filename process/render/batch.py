import logging
import sys

from process.camera.utils import restore_initial_camera
from process.init.exit_summary import (
    emit_exit_summary, finalize_logs, print_divider,
)
from process.init.shutdown import graceful_shutdown
from process.mode.default import apply_default_reset
from process.plotter.state import (
    _STARTUP_FLAG_MAP, _SMOOTH_STARTUP_MAP, valid_modes_for,
    ALL_MODE_TOKEN, expand_all_modes,
)
from process.overlay import init_sysinfo_monitor
from process.render.loop import render_loop

logger = logging.getLogger(__name__)

_INPLACE_WIDTH = 40

def _apply_mode(plotter, mode: str) -> None:
    apply_default_reset(plotter)
    idx = _SMOOTH_STARTUP_MAP.get(mode)
    if idx is not None:
        plotter._is_smooth = True
        plotter._smooth_cycle = idx
        if idx == 0:
            plotter._is_tex = True
        elif idx == 1:
            plotter._is_lighting = True
        else:
            plotter._is_lighting = True
            plotter._is_tex = True
            plotter._pbr_with_tex = True
        return
    flag = _STARTUP_FLAG_MAP.get(mode)
    if flag:
        setattr(plotter, flag, True)

def resolve_batch_modes(plotter, modes) -> list:
    is_pc = getattr(plotter, '_n_faces', 1) == 0
    allowed = valid_modes_for(is_pc)
    if ALL_MODE_TOKEN in modes:
        expanded = []
        for mode in modes:
            expanded.extend(
                expand_all_modes(is_pc) if mode == ALL_MODE_TOKEN
                else [mode]
            )

        modes = list(dict.fromkeys(expanded))
        logger.info('[BATCH] %s -> %s', ALL_MODE_TOKEN, modes)
    usable, skipped = [], []
    for mode in modes:
        (usable if mode in allowed else skipped).append(mode)
    if skipped:
        logger.warning(
            '[BATCH] Skipping %s: not available for this input type %s',
            skipped, sorted(allowed),
        )
    return usable

def batch_title(index: int, total: int, mode: str) -> str:
    return f'BATCH {index}/{total} ({mode.upper()})'

def _print_inplace(text: str) -> None:
    sys.stdout.write(f'\r{text:<{_INPLACE_WIDTH}}')
    sys.stdout.flush()

def _start_mode(plotter, mode: str, index: int, total: int,
                save_path) -> None:
    _apply_mode(plotter, mode)
    restore_initial_camera(plotter)
    plotter._idx = 0
    plotter._save_path = save_path
    plotter._batch_index = index
    plotter._batch_total = total
    plotter._batch_last = index == total
    plotter._batch_title = batch_title(index, total, mode)
    if getattr(plotter, '_sysinfo_thread', None) is None or not (
        plotter._sysinfo_thread.is_alive()
    ):
        init_sysinfo_monitor(plotter)
    logger.info('[BATCH] %d/%d start: %s', index, total, mode)
    if not save_path:

        _print_inplace(plotter._batch_title)

def _emit_batch_summary(plotter, buffer, total: int) -> None:
    targets = getattr(plotter, '_batch_targets', None)
    if not targets:
        return

    graceful_shutdown(plotter, 'batch')
    name = getattr(plotter, '_input_name', '?')
    frames = getattr(buffer, 'total', 0) or 0
    count = getattr(plotter, '_batch_saved_count', 0)
    finalize_logs(
        name, frames, getattr(plotter, '_start_time', None),
        count, targets[-1],
    )
    emit_exit_summary(
        name, frames, count, targets,
        headless=True, count_suffix=f'BATCH {total}/{total}',
    )

def run_batch(plotter, buffer, modes) -> None:
    usable = resolve_batch_modes(plotter, modes)
    if not usable:
        logger.error('[BATCH] No runnable mode - falling back to default.')
        render_loop(plotter, buffer)
        return

    save_path = getattr(plotter, '_save_path', None)
    total = len(usable)
    plotter._batch_active = True
    plotter._batch_targets = []
    if save_path:

        print_divider()
    for index, mode in enumerate(usable, start=1):
        _start_mode(plotter, mode, index, total, save_path)
        render_loop(plotter, buffer)
        logger.info('[BATCH] %d/%d done: %s', index, total, mode)
    plotter._batch_active = False
    plotter._batch_title = None
    if not save_path:
        sys.stdout.write('\n')
        sys.stdout.flush()
    logger.info('[BATCH] All %d modes finished.', total)
    _emit_batch_summary(plotter, buffer, total)
