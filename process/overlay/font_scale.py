import logging

import vtk

from configs.settings import (
    WINDOW_WIDTH, UI_LOG_MAX_CHARS, UI_LOG_MIN_CHARS, UI_LOG_PAD_PX,
)

logger = logging.getLogger(__name__)

_ATTR_PROPS = '_font_scaled_props'
_ATTR_WIDTH = '_font_scale_width'

_SAMPLE_TEXT = 'M' * 200
_SAMPLE_DPI = 72
_FALLBACK_RATIO = 0.6

def measure_char_width(prop) -> float:
    bbox = [0, 0, 0, 0]
    tools = vtk.vtkFreeTypeTools.GetInstance()
    if not tools.GetBoundingBox(prop, _SAMPLE_TEXT, _SAMPLE_DPI, bbox):
        return prop.GetFontSize() * _FALLBACK_RATIO
    width = (bbox[1] - bbox[0] + 1) / len(_SAMPLE_TEXT)
    return width if width > 0 else prop.GetFontSize() * _FALLBACK_RATIO

def compute_log_max_chars(plotter, prop) -> int:
    if UI_LOG_MAX_CHARS > 0:
        return UI_LOG_MAX_CHARS
    rw = getattr(plotter, 'render_window', None)
    width = rw.GetSize()[0] if rw is not None else WINDOW_WIDTH
    avail = max(1, width - 2 * UI_LOG_PAD_PX)
    return max(UI_LOG_MIN_CHARS, int(avail / measure_char_width(prop)))

def current_scale(plotter) -> float:
    rw = getattr(plotter, 'render_window', None)
    if rw is None or not WINDOW_WIDTH:
        return 1.0
    return rw.GetSize()[0] / WINDOW_WIDTH

def register_text_prop(plotter, prop, base_size: int) -> None:
    props = getattr(plotter, _ATTR_PROPS, None)
    if props is None:
        props = []
        setattr(plotter, _ATTR_PROPS, props)
    props.append((prop, base_size))
    scale = current_scale(plotter)
    prop.SetFontSize(max(1, round(base_size * scale)))

def update_font_scale(plotter) -> bool:
    props = getattr(plotter, _ATTR_PROPS, None)
    if not props:
        return False
    rw = getattr(plotter, 'render_window', None)
    if rw is None:
        return False
    width = rw.GetSize()[0]
    if width == getattr(plotter, _ATTR_WIDTH, WINDOW_WIDTH):
        return False
    setattr(plotter, _ATTR_WIDTH, width)
    scale = width / WINDOW_WIDTH if WINDOW_WIDTH else 1.0
    for prop, base in props:
        prop.SetFontSize(max(1, round(base * scale)))
    logger.debug(
        'Font scale updated: width=%d scale=%.3f (%d props)',
        width, scale, len(props),
    )
    return True
