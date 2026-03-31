import time

from configs.keybinding import (
    KEY_MESH_DEFAULT, KEY_SMOOTH, KEY_SMOOTH_SHADING,
    KEY_HELP, KEY_EDGE,
    KEY_CAM_RESET, KEY_CENTER_VIEW, KEY_CAM_PROJ, KEY_LIGHT,
    KEY_SCREENSHOT, KEY_GRID,
    KEY_VTX, KEY_WIRE, KEY_ISO,
    KEY_NORMAL_COLOR, KEY_MESH_QUALITY,
    KEY_FACE_NORMAL, KEY_DEPTH,
    KEY_BACKFACE, KEY_ACTOR_NEXT,
    KEY_VIEW_FRONT, KEY_VIEW_BACK, KEY_VIEW_TOP, KEY_VIEW_SIDE,
    KEY_FIRST_FRAME, KEY_LAST_FRAME,
    KEY_STEP_FWD, KEY_STEP_BWD,
    KEY_KP_ZOOM_IN, KEY_KP_ZOOM_OUT, KEY_KP_DOLLY_IN, KEY_KP_DOLLY_OUT,
    KEY_INC, KEY_DEC,
)
from process.keys import reset, smooth, modes, axis, vtx_pick

def _make_blocked(*keys) -> frozenset:
    result = set()
    for k in keys:
        if isinstance(k, (list, tuple)):
            result.update(k)
        else:
            result.add(k)
    return frozenset(result)

_BLOCKED_KEYS = _make_blocked(
    KEY_MESH_DEFAULT, KEY_SMOOTH, KEY_SMOOTH_SHADING,
    KEY_HELP, KEY_EDGE,
    KEY_CAM_RESET, KEY_CENTER_VIEW, KEY_CAM_PROJ, KEY_LIGHT,
    KEY_SCREENSHOT, KEY_GRID,
    KEY_VTX, KEY_WIRE, KEY_ISO,
    KEY_NORMAL_COLOR, KEY_MESH_QUALITY,
    KEY_FACE_NORMAL, KEY_DEPTH,
    KEY_BACKFACE, KEY_ACTOR_NEXT,
    KEY_VIEW_FRONT, KEY_VIEW_BACK, KEY_VIEW_TOP, KEY_VIEW_SIDE,
    KEY_FIRST_FRAME, KEY_LAST_FRAME,
    KEY_STEP_FWD, KEY_STEP_BWD,
    KEY_KP_ZOOM_IN, KEY_KP_ZOOM_OUT, KEY_KP_DOLLY_IN, KEY_KP_DOLLY_OUT,
    KEY_INC, KEY_DEC,
    'plus', 'minus',
    'p',
)

def apply_key_filter_style(plotter):
    interactor = plotter.iren.interactor

    def _block_char(caller, _):
        if caller.GetKeySym() in _BLOCKED_KEYS:
            caller.SetKeySym('')
            caller.SetKeyCode('\x00')

    def _dispatch_special(caller, _):
        key = caller.GetKeySym()
        if caller.GetControlKey():
            cb = plotter._ctrl_key_dispatch.get(key)
        else:
            cb = plotter._special_key_dispatch.get(key)
        if cb is not None:
            cb()
            caller.SetKeySym('')
            caller.SetKeyCode('\x00')

    interactor.AddObserver('CharEvent', _block_char, 1.0)
    interactor.AddObserver('KeyPressEvent', _dispatch_special, 1.0)

def register_callbacks(plotter, total_len):
    p = plotter

    def trigger():
        p._needs_update = True

    def set_mode(msg: str):
        p._mode_msg = msg
        p._mode_msg_time = time.time()

    reset.register(p, trigger, set_mode, total_len)
    apply_smooth_cycle = smooth.register(p, trigger, set_mode)
    modes.register(p, trigger, set_mode)
    axis.register(p, trigger, set_mode, apply_smooth_cycle)
    vtx_pick.register(p, trigger)
