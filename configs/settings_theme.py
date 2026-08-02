THEME = 'black'

def _invert_hex(color: str) -> str:
    h = color.lstrip('#')
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f'#{255 - r:02X}{255 - g:02X}{255 - b:02X}'

def apply_theme(color: str) -> str:
    return _invert_hex(color) if THEME == 'white' else color

def toggle_theme() -> None:
    global THEME
    THEME = 'white' if THEME == 'black' else 'black'

def set_fontsize(pt: int, scale: float) -> int:
    return max(1, round(pt * scale))

def make_fontsize_fn(scale: float):
    def _fn(pt: int) -> int:
        return set_fontsize(pt, scale)
    return _fn
