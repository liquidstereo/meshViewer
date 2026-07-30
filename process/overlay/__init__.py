import logging
import vtk

from process.overlay.hud_texts import (
    init_status_text, update_status_text,
    init_sysinfo_monitor,
    init_mode_text, update_mode_text,
    init_log_overlay, update_log_overlay,
    init_help_overlay,
    init_colorbar, update_colorbar,
    update_periodic_overlays,
    init_overlay_text, update_overlay_text,
)
from process.overlay.sequence import init_sequence_overlay, load_seq_files
from configs.settings import (
    DISPLAY_STATUS, DISPLAY_SYSINFO, DISPLAY_MODE, DISPLAY_LOG,
    DISPLAY_COLORBAR, DISPLAY_HELP,
)

logger = logging.getLogger(__name__)

_LAYER_SCENE  = 0
_LAYER_HUD    = 2
_LAYER_HELP   = 3
_TOTAL_LAYERS = _LAYER_HELP + 1

def _make_overlay_renderer(rw, layer: int) -> vtk.vtkRenderer:
    r = vtk.vtkRenderer()
    r.SetLayer(layer)
    r.InteractiveOff()
    r.PreserveColorBufferOn()
    r.PreserveDepthBufferOn()
    rw.AddRenderer(r)
    return r

def _init_hud_renderer(plotter) -> None:
    rw = plotter.render_window
    rw.SetNumberOfLayers(max(rw.GetNumberOfLayers(), _TOTAL_LAYERS))
    hud_r = _make_overlay_renderer(rw, _LAYER_HUD)
    plotter._hud_renderer = hud_r

    for attr in ('_vtx_label_actor', '_vtx_pick_text'):
        actor = getattr(plotter, attr, None)
        if actor is not None:
            plotter.renderer.RemoveActor2D(actor)
            hud_r.AddActor2D(actor)
    logger.debug(
        '_init_hud_renderer: registered (Layer %d)', _LAYER_HUD
    )

def init_overlays(plotter) -> None:
    plotter.render_window.SetNumberOfLayers(_TOTAL_LAYERS)

    if DISPLAY_STATUS:
        init_status_text(plotter)
    if DISPLAY_SYSINFO:
        init_sysinfo_monitor(plotter)
    _init_hud_renderer(plotter)
    if DISPLAY_MODE:
        init_mode_text(plotter)
    if DISPLAY_LOG:
        init_log_overlay(plotter)
    if DISPLAY_COLORBAR:
        init_colorbar(plotter)
    if DISPLAY_HELP:
        init_help_overlay(plotter)
    logger.info(
        'init_overlays: status=%s sysinfo=%s mode=%s log=%s'
        ' colorbar=%s help=%s',
        DISPLAY_STATUS, DISPLAY_SYSINFO, DISPLAY_MODE, DISPLAY_LOG,
        DISPLAY_COLORBAR, DISPLAY_HELP,
    )

__all__ = [
    'init_status_text', 'update_status_text',
    'init_sysinfo_monitor',
    'init_mode_text', 'update_mode_text',
    'init_log_overlay', 'update_log_overlay',
    'init_help_overlay',
    'init_colorbar', 'update_colorbar',
    'init_sequence_overlay',
    'load_seq_files',
    'update_periodic_overlays',
    'init_overlay_text', 'update_overlay_text',
    'init_overlays',
    '_init_hud_renderer',
]
