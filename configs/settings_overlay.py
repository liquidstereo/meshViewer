from configs.settings_theme import apply_theme as _apply_theme
from configs.settings_font import _font_scale, _set_fontsize, FONT
from configs.settings_window import WINDOW_WIDTH, WINDOW_HEIGHT

DISPLAY_STATUS      = True
DISPLAY_SYSINFO     = True
DISPLAY_MODE        = True
DISPLAY_LOG         = True
DISPLAY_COLORBAR    = True
DISPLAY_HELP        = True
DISPLAY_SEQUENCE    = True
DISPLAY_AXES        = True

DISPLAY_CAM_DETAILS = False

DISPLAY_SEQ_ROUND   = True

UI_STATUS_FONT_SIZE     = _set_fontsize(15)
UI_STATUS_LINE_SPACING  = 1.10
UI_STATUS_COLOR         = _apply_theme('#DADADA')
UI_STATUS_PAD_PX        = 10
UI_STATUS_PAD_PY        = 15

UI_SYSINFO_FONT_SIZE    = _set_fontsize(15)
UI_SYSINFO_COLOR        = _apply_theme('#DADADA')
UI_SYSINFO_PAD_PX       = UI_STATUS_PAD_PX
UI_SYSINFO_PAD_PY       = UI_STATUS_PAD_PX

UI_LOG_FONT_SIZE    = _set_fontsize(12)
UI_LOG_COLOR        = _apply_theme('#686868')
UI_LOG_ERROR_COLOR  = '#FF0000'
UI_LOG_PAD_PX       = 10
UI_LOG_PAD_PY       = 10

UI_LOG_FORMAT       = '%(asctime)s | %(levelname)-8s | %(message)s'

UI_LOG_MAX_CHARS    = 0
UI_LOG_MIN_CHARS    = 20
UI_LOG_ELLIPSIS     = '...'

UI_MODE_FONT_SIZE   = _set_fontsize(15)
UI_MODE_COLOR       = _apply_theme('#FFC400')
UI_MODE_BACKGROUND  = _apply_theme('#FD1212')
UI_MODE_PAD_PX      = UI_STATUS_PAD_PY
UI_MODE_PAD_PY      = UI_MODE_PAD_PX
MODE_MSG_DURATION   = 3.0
ERROR_MSG_DURATION  = 3.0

UI_HELP_FONT_SIZE   = _set_fontsize(14)
UI_HELP_COLOR       = _apply_theme('#DDDDDD')
UI_HELP_BG_OPACITY  = 0.75
UI_HELP_TEXT_W      = round(310 * _font_scale)
UI_HELP_TEXT_H      = round(430 * _font_scale)
UI_HELP_POS_X       = (WINDOW_WIDTH  - UI_HELP_TEXT_W) // 2
UI_HELP_POS_Y       = (WINDOW_HEIGHT - UI_HELP_TEXT_H) // 2

UI_COLORBAR_WIDTH           = 0.10
UI_COLORBAR_HEIGHT          = 0.40
UI_COLORBAR_POS_X           = 0.925
UI_COLORBAR_POS_Y           = 0.30
UI_COLORBAR_FONT_FAMILY     = FONT
UI_COLORBAR_TITLE_FONT_SIZE = 0
UI_COLORBAR_LABEL_FONT_SIZE = _set_fontsize(10)
UI_COLORBAR_TITLE_COLOR     = _apply_theme('#DADADA')
UI_COLORBAR_LABEL_COLOR     = _apply_theme('#DADADA')
UI_COLORBAR_NLABELS         = 5
UI_COLORBAR_BAR_RATIO       = 0.19

SEQ_SIZE_W          = 0.425
SEQ_PAD_RIGHT_PX    = 10
SEQ_PAD_BOTTOM_PX   = 10
SEQ_IMAGE_EXTS      = ('.png', '.jpg', '.jpeg', '.bmp')

SEQ_ROUND_RADIUS_PX = round(12 * _font_scale)
SEQ_ROUND_SS        = 4
