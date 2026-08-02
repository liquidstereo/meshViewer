import configs.settings_theme as _theme

THEME_NORMAL = 'black'
THEME_INVERT = 'white'

def invert_hex(color: str) -> str:
    h = color.lstrip('#')
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f'#{255 - r:02X}{255 - g:02X}{255 - b:02X}'

def current_theme() -> str:
    return _theme.THEME

def apply_theme(color: str) -> str:
    if _theme.THEME == THEME_INVERT:
        return invert_hex(color)
    return color

def toggle_theme() -> None:
    _theme.THEME = (
        THEME_INVERT if _theme.THEME == THEME_NORMAL else THEME_NORMAL
    )

def set_fontsize(pt: int, scale: float) -> int:
    return max(1, round(pt * scale))

def make_fontsize_fn(scale: float):
    def _fn(pt: int) -> int:
        return set_fontsize(pt, scale)
    return _fn
