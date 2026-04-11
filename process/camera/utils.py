import numpy as np

_MAX_ELEVATION = 85.0

def cam_zoom(plotter, cam, factor: float) -> None:
    if cam.GetParallelProjection():
        cam.SetParallelScale(cam.GetParallelScale() / factor)
    else:
        cam.Zoom(factor)
    plotter.renderer.ResetCameraClippingRange()

def cam_dolly(plotter, cam, factor: float) -> None:
    cam.Dolly(factor)
    plotter.renderer.ResetCameraClippingRange()

def cam_rotate_y(plotter, cam, deg: float) -> None:
    cam.Azimuth(deg)
    plotter.renderer.ResetCameraClippingRange()

def cam_rotate_x_rodrigues(
    plotter,
    cam,
    deg: float,
    max_elev: float = _MAX_ELEVATION,
) -> None:
    current = getattr(plotter, '_rot_elev', 0.0)
    new_elev = max(-max_elev, min(max_elev, current + deg))
    delta = new_elev - current
    if delta == 0.0:
        plotter.renderer.ResetCameraClippingRange()
        return
    rad = np.radians(delta)
    focal = np.array(cam.GetFocalPoint())
    pos = np.array(cam.GetPosition())
    arm = pos - focal
    view_dir = -arm / np.linalg.norm(arm)
    view_up = np.array(cam.GetViewUp())
    right = np.cross(view_dir, view_up)
    r_norm = np.linalg.norm(right)
    if r_norm > 1e-8:
        right /= r_norm
        cos_a = np.cos(rad)
        sin_a = np.sin(rad)
        new_arm = (
            cos_a * arm
            + sin_a * np.cross(right, arm)
            + (1.0 - cos_a) * np.dot(right, arm) * right
        )
        new_up = (
            cos_a * view_up
            + sin_a * np.cross(right, view_up)
            + (1.0 - cos_a) * np.dot(right, view_up) * right
        )
        cam.SetViewUp(*new_up)
        cam.SetPosition(*(focal + new_arm))
    plotter._rot_elev = new_elev
    plotter.renderer.ResetCameraClippingRange()
