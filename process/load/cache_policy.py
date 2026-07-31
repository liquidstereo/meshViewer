import os
import logging

import numpy as np

from configs.settings import (
    AUTO_DECIMATE_THRESHOLD, AUTO_DECIMATE_MAX_CELLS,
    AUTO_DECIMATE_MAX_RATIO, AUTO_DECIMATE_MIN_GAIN_RATIO,
    CACHE_POINTS_FLOAT32, CACHE_NORMALS, STARTUP_MODE,
    DEFAULT_SMOOTH,
)

logger = logging.getLogger(__name__)

_FLOAT32_SAFE_MAX = 3.0e38

def decimate_skip_limit() -> float:
    return AUTO_DECIMATE_MAX_CELLS * (1.0 + AUTO_DECIMATE_MIN_GAIN_RATIO)

def should_decimate(n_faces: int, has_tcoords: bool) -> bool:
    if has_tcoords:
        return False
    if n_faces <= AUTO_DECIMATE_THRESHOLD:
        return False
    if n_faces <= decimate_skip_limit():
        return False
    return True

def decimate_ratio(n_faces: int) -> float:
    if n_faces <= 0:
        return 0.0
    return min(
        AUTO_DECIMATE_MAX_RATIO,
        n_faces / AUTO_DECIMATE_MAX_CELLS,
    )

def cache_points_array(points: np.ndarray) -> np.ndarray:
    if not CACHE_POINTS_FLOAT32:
        return points
    if points.dtype == np.float32:
        return points
    if points.size == 0:
        return np.ascontiguousarray(points, dtype=np.float32)
    max_abs = float(np.abs(points).max())
    if not np.isfinite(max_abs) or max_abs > _FLOAT32_SAFE_MAX:
        logger.warning(
            'Cache points kept as %s: value out of float32 range'
            ' (max_abs=%g).',
            points.dtype, max_abs,
        )
        return points
    return np.ascontiguousarray(points, dtype=np.float32)

_NORMALS_MODES = frozenset({
    'smooth', 'pbr_tex.tex', 'pbr_tex.pbr', 'pbr_tex',
    'isoline', 'wire', 'normal_color',
})

ENV_NO_NORMAL = 'MESHVIEWER_NO_NORMAL'

ENV_STARTUP_MODE = 'MESHVIEWER_STARTUP_MODE'

def set_startup_mode(mode: str | None) -> None:
    if mode:
        os.environ[ENV_STARTUP_MODE] = mode
    else:
        os.environ.pop(ENV_STARTUP_MODE, None)

def startup_mode_override() -> str | None:
    return os.environ.get(ENV_STARTUP_MODE) or None

def effective_startup_mode(default: str = STARTUP_MODE) -> str:
    return startup_mode_override() or default

def set_no_normal(disabled: bool) -> None:
    if disabled:
        os.environ[ENV_NO_NORMAL] = '1'
    else:
        os.environ.pop(ENV_NO_NORMAL, None)

def no_normal_requested() -> bool:
    return os.environ.get(ENV_NO_NORMAL) == '1'

def mode_needs_normals(mode: str) -> bool:
    return mode in _NORMALS_MODES

def resolve_cache_normals(mode: str, has_faces: bool,
                          setting=CACHE_NORMALS) -> bool:
    if not has_faces:
        return False
    if no_normal_requested():
        return False
    if setting is True:
        return True
    if setting is False:
        return False

    return mode_needs_normals(mode) or DEFAULT_SMOOTH
