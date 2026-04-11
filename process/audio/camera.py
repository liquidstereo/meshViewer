import logging

from configs.defaults import (
    AUDIO_CAM_POSITION, AUDIO_CAM_FOCAL_POINT, AUDIO_CAM_UP,
)
from configs.keybinding import TURNTABLE_ROT_STEP
from process.camera.utils import (
    cam_zoom, cam_dolly,
    cam_rotate_y, cam_rotate_x_rodrigues,
)

logger = logging.getLogger(__name__)

def setup_audio_cam(plotter) -> None:
    cam = plotter.renderer.GetActiveCamera()
    cam.SetViewUp(*AUDIO_CAM_UP)
    cam.SetPosition(*AUDIO_CAM_POSITION)
    cam.SetFocalPoint(*AUDIO_CAM_FOCAL_POINT)
    plotter._rot_elev = 0.0
    plotter.renderer.ResetCameraClippingRange()

def _reset_cam(plotter, cam) -> None:
    cam.SetViewUp(*AUDIO_CAM_UP)
    cam.SetPosition(*AUDIO_CAM_POSITION)
    cam.SetFocalPoint(*AUDIO_CAM_FOCAL_POINT)
    plotter._rot_elev = 0.0
    plotter.renderer.ResetCameraClippingRange()
    plotter.render()

def _center_view(plotter, cam) -> None:
    bounds = plotter.renderer.ComputeVisiblePropBounds()
    cx = (bounds[0] + bounds[1]) / 2
    cy = (bounds[2] + bounds[3]) / 2
    cz = (bounds[4] + bounds[5]) / 2
    cam.SetFocalPoint(cx, cy, cz)
    plotter.renderer.ResetCameraClippingRange()
    plotter.render()

def _toggle_proj(plotter, cam, set_mode_msg) -> None:
    cam.SetParallelProjection(not cam.GetParallelProjection())
    mode = 'PARALLEL' if cam.GetParallelProjection() else 'PERSPECTIVE'
    set_mode_msg(mode)
    plotter.render()

def make_cam_callbacks(plotter, set_mode_msg: callable) -> dict:
    cam = plotter.renderer.GetActiveCamera()
    return {
        'reset':       lambda: _reset_cam(plotter, cam),
        'zoom_in':     lambda: (
            cam_zoom(plotter, cam, 1.1), plotter.render()
        ),
        'zoom_out':    lambda: (
            cam_zoom(plotter, cam, 0.9), plotter.render()
        ),
        'dolly_in':    lambda: (
            cam_dolly(plotter, cam, 1.1), plotter.render()
        ),
        'dolly_out':   lambda: (
            cam_dolly(plotter, cam, 0.9), plotter.render()
        ),
        'rot_yl':      lambda: (
            cam_rotate_y(plotter, cam, -TURNTABLE_ROT_STEP),
            plotter.render(),
        ),
        'rot_yr':      lambda: (
            cam_rotate_y(plotter, cam, TURNTABLE_ROT_STEP),
            plotter.render(),
        ),
        'rot_xd':      lambda: (
            cam_rotate_x_rodrigues(plotter, cam, -TURNTABLE_ROT_STEP),
            plotter.render(),
        ),
        'rot_xu':      lambda: (
            cam_rotate_x_rodrigues(plotter, cam, TURNTABLE_ROT_STEP),
            plotter.render(),
        ),
        'center_view': lambda: _center_view(plotter, cam),
        'toggle_proj': lambda: _toggle_proj(plotter, cam, set_mode_msg),
    }
