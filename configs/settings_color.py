from configs.theme import apply_theme as _apply_theme
from configs.settings_font import _set_fontsize

COLOR_BG         = _apply_theme('#000000')
COLOR_GRID       = _apply_theme('#7A7A7A')
COLOR_BBOX       = _apply_theme('#7A7A7A')
GRID_WIDTH       = 1.0
BBOX_WIDTH       = 1.0

MESH_MATTE_COLOR = None

AXIS_FONT_SIZE  = _set_fontsize(13)
AXIS_VIEWPORT   = (0, 0, 0.12, 0.12)
AXIS_NAMES      = {0: 'X', 1: 'Y', 2: 'Z'}
AXIS_COLORS     = [(1, 0.4, 0.4), (0.4, 1, 0.4), (0.4, 0.4, 1)]
