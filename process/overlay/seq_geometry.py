import logging

import numpy as np
import vtk
from vtkmodules.util.numpy_support import numpy_to_vtk

from configs.settings import (
    SEQ_SIZE_W, SEQ_PAD_RIGHT_PX, SEQ_PAD_BOTTOM_PX,
    SEQ_ROUND_RADIUS_PX, WINDOW_WIDTH,
)

logger = logging.getLogger(__name__)

def scaled_radius(win_w: int) -> int:
    base = WINDOW_WIDTH if WINDOW_WIDTH else win_w
    scale = win_w / base if base else 1.0
    return max(0, round(SEQ_ROUND_RADIUS_PX * scale))

def calc_viewport(win_w: int, win_h: int,
                  img_w: int, img_h: int) -> tuple:
    pad_r = SEQ_PAD_RIGHT_PX / max(1, win_w)
    pad_b = SEQ_PAD_BOTTOM_PX / max(1, win_h)
    vp_h_px = SEQ_SIZE_W * win_w * max(1, img_h) / max(1, img_w)
    seq_size_h = vp_h_px / max(1, win_h)
    return (
        1.0 - SEQ_SIZE_W - pad_r,
        pad_b,
        1.0 - pad_r,
        seq_size_h + pad_b,
    )

def viewport_px(viewport: tuple, win_w: int, win_h: int) -> tuple:
    w = max(1, int((viewport[2] - viewport[0]) * win_w))
    h = max(1, int((viewport[3] - viewport[1]) * win_h))
    return w, h

def make_corner_alpha(width: int, height: int, radius: int,
                      supersample: int = 4) -> np.ndarray:
    w = max(1, int(width))
    h = max(1, int(height))
    alpha = np.full((h, w), 255, dtype=np.uint8)

    r = int(min(radius, w // 2, h // 2))
    if r <= 0:
        return alpha

    ss = max(1, int(supersample))
    grid = (np.arange(r * ss) + 0.5) / ss
    dist_sq = (grid - r) ** 2
    inside = (dist_sq[:, None] + dist_sq[None, :]) <= float(r * r)
    coverage = inside.reshape(r, ss, r, ss).mean(axis=(1, 3))
    corner = np.round(coverage * 255.0).astype(np.uint8)

    alpha[:r, :r] = corner
    alpha[:r, w - r:] = corner[:, ::-1]
    alpha[h - r:, :r] = corner[::-1, :]
    alpha[h - r:, w - r:] = corner[::-1, ::-1]
    return alpha

def build_alpha_image(alpha: np.ndarray) -> vtk.vtkImageData:
    h, w = alpha.shape
    arr = numpy_to_vtk(
        np.ascontiguousarray(alpha).reshape(-1),
        deep=True,
        array_type=vtk.VTK_UNSIGNED_CHAR,
    )
    arr.SetName('SeqAlpha')

    image = vtk.vtkImageData()
    image.SetDimensions(w, h, 1)
    image.GetPointData().SetScalars(arr)
    return image
