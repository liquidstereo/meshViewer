from configs.settings import (
    ISO_AXIS_DEFAULT, WIRE_AXIS_DEFAULT,
    FNORMAL_AXIS_DEFAULT, DEPTH_AXIS_DEFAULT,
    STARTUP_AXIS,
    STARTUP_REVERSE_X_AXIS, STARTUP_REVERSE_Y_AXIS, STARTUP_REVERSE_Z_AXIS,
    FLIP_OBJECT_X, FLIP_OBJECT_Y, FLIP_OBJECT_Z,
    MESH_STARTUP_AXIS,
    MESH_STARTUP_REVERSE_X_AXIS, MESH_STARTUP_REVERSE_Y_AXIS,
    MESH_STARTUP_REVERSE_Z_AXIS,
    MESH_FLIP_OBJECT_X, MESH_FLIP_OBJECT_Y, MESH_FLIP_OBJECT_Z,
    PT_STARTUP_AXIS,
    PT_STARTUP_REVERSE_X_AXIS, PT_STARTUP_REVERSE_Y_AXIS,
    PT_STARTUP_REVERSE_Z_AXIS,
    PT_FLIP_OBJECT_X, PT_FLIP_OBJECT_Y, PT_FLIP_OBJECT_Z,
    NP_STARTUP_AXIS,
    NP_STARTUP_REVERSE_X_AXIS, NP_STARTUP_REVERSE_Y_AXIS,
    NP_STARTUP_REVERSE_Z_AXIS,
    NP_FLIP_OBJECT_X, NP_FLIP_OBJECT_Y, NP_FLIP_OBJECT_Z,
    AUDIO_STARTUP_AXIS,
    AUDIO_STARTUP_REVERSE_X_AXIS, AUDIO_STARTUP_REVERSE_Y_AXIS,
    AUDIO_STARTUP_REVERSE_Z_AXIS,
    AUDIO_FLIP_OBJECT_X, AUDIO_FLIP_OBJECT_Y, AUDIO_FLIP_OBJECT_Z,
)

_AXIS_TOKENS = {'X': 0, 'Y': 1, 'Z': 2, 'CAM': 3}
_AXIS_CAM = _AXIS_TOKENS['CAM']

_ID_STYLE_TOKENS = {'FLAT': 0, 'SHADED': 1}
_ID_STYLE_FALLBACK = _ID_STYLE_TOKENS['SHADED']

ID_SHADERS = ('default', 'smooth', 'pbr')
_ID_SHADER_FALLBACK = ID_SHADERS[0]

_MODE_AXIS_SETTINGS = {
    '_iso_axis': ISO_AXIS_DEFAULT,
    '_wire_axis': WIRE_AXIS_DEFAULT,
    '_fnormal_axis': FNORMAL_AXIS_DEFAULT,
    '_depth_axis': DEPTH_AXIS_DEFAULT,
}

def resolve_mode_axis(value) -> int:
    if isinstance(value, str):
        return _AXIS_TOKENS.get(value.strip().upper(), _AXIS_CAM)
    if isinstance(value, bool):
        return _AXIS_CAM
    if isinstance(value, int) and 0 <= value <= _AXIS_CAM:
        return value
    return _AXIS_CAM

def resolve_id_style(value) -> int:
    if isinstance(value, str):
        return _ID_STYLE_TOKENS.get(
            value.strip().upper(), _ID_STYLE_FALLBACK,
        )
    if isinstance(value, bool):
        return _ID_STYLE_FALLBACK
    if isinstance(value, int) and 0 <= value < len(_ID_STYLE_TOKENS):
        return value
    return _ID_STYLE_FALLBACK

def resolve_id_shader(value) -> str:
    if not isinstance(value, str):
        return _ID_SHADER_FALLBACK
    name = value.strip().lower()
    return name if name in ID_SHADERS else _ID_SHADER_FALLBACK

def apply_mode_axes(plotter) -> None:
    for attr, value in _MODE_AXIS_SETTINGS.items():
        setattr(plotter, attr, resolve_mode_axis(value))

def resolve_axis_settings(file_type: str) -> tuple:
    _overrides = {
        'mesh': (
            MESH_STARTUP_AXIS,
            MESH_STARTUP_REVERSE_X_AXIS,
            MESH_STARTUP_REVERSE_Y_AXIS,
            MESH_STARTUP_REVERSE_Z_AXIS,
            MESH_FLIP_OBJECT_X,
            MESH_FLIP_OBJECT_Y,
            MESH_FLIP_OBJECT_Z,
        ),
        'point_cloud': (
            PT_STARTUP_AXIS,
            PT_STARTUP_REVERSE_X_AXIS,
            PT_STARTUP_REVERSE_Y_AXIS,
            PT_STARTUP_REVERSE_Z_AXIS,
            PT_FLIP_OBJECT_X,
            PT_FLIP_OBJECT_Y,
            PT_FLIP_OBJECT_Z,
        ),
        'np_data': (
            NP_STARTUP_AXIS,
            NP_STARTUP_REVERSE_X_AXIS,
            NP_STARTUP_REVERSE_Y_AXIS,
            NP_STARTUP_REVERSE_Z_AXIS,
            NP_FLIP_OBJECT_X,
            NP_FLIP_OBJECT_Y,
            NP_FLIP_OBJECT_Z,
        ),
        'audio': (
            AUDIO_STARTUP_AXIS,
            AUDIO_STARTUP_REVERSE_X_AXIS,
            AUDIO_STARTUP_REVERSE_Y_AXIS,
            AUDIO_STARTUP_REVERSE_Z_AXIS,
            AUDIO_FLIP_OBJECT_X,
            AUDIO_FLIP_OBJECT_Y,
            AUDIO_FLIP_OBJECT_Z,
        ),
    }
    _defaults = (
        STARTUP_AXIS,
        STARTUP_REVERSE_X_AXIS,
        STARTUP_REVERSE_Y_AXIS,
        STARTUP_REVERSE_Z_AXIS,
        FLIP_OBJECT_X,
        FLIP_OBJECT_Y,
        FLIP_OBJECT_Z,
    )
    overrides = _overrides.get(file_type, (None,) * 7)
    return tuple(
        o if o is not None else d
        for o, d in zip(overrides, _defaults)
    )
