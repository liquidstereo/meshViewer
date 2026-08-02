from core.theme import make_fontsize_fn as _make_fontsize_fn
from configs.settings_window import WINDOW_WIDTH as _WINDOW_WIDTH

FONT_PRIORITY: tuple[str, ...] = (
    'Ubuntu Sans Mono',
    'DejaVu Sans Mono',
    'Noto Sans Mono',
    'Liberation Mono',
    'monospace',
)
FONT = FONT_PRIORITY[0]

GRID_FONT_FAMILY = 'courier'
UI_FONT_FAMILY   = FONT

FONT_REF_WIDTH = 1080

FONT_USER_SCALE = 1.0

_font_scale   = FONT_USER_SCALE * (_WINDOW_WIDTH / FONT_REF_WIDTH)
_set_fontsize = _make_fontsize_fn(_font_scale)
