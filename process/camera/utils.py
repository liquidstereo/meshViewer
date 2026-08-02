import numpy as np

_MAX_ELEVATION = 85.0
_EPS = 1e-8
_MIN_VIEW_ANGLE = 1e-03
_MAX_VIEW_ANGLE = 179.0

def _cam_basis(cam) -> tuple:
    fwd = np.array(cam.GetDirectionOfProjection(), dtype=float)
    up = np.array(cam.GetViewUp(), dtype=float)
    fwd_n = np.linalg.norm(fwd)
    up_n = np.linalg.norm(up)
    if fwd_n > _EPS:
        fwd = fwd / fwd_n
    if up_n > _EPS:
        up = up / up_n
    right = np.cross(fwd, up)
    right_n = np.linalg.norm(right)
    if right_n > _EPS:
        right = right / right_n
    return fwd, up, right

def _shift_cam(cam, offset, move_focal: bool) -> None:
    cam.SetPosition(*(np.array(cam.GetPosition()) + offset))
    if move_focal:
        cam.SetFocalPoint(*(np.array(cam.GetFocalPoint()) + offset))

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

def set_parallel_projection(plotter, cam, enable: bool) -> None:
    enable = bool(enable)
    if bool(cam.GetParallelProjection()) == enable:
        return

    dist = float(cam.GetDistance())
    if dist > _EPS:
        if enable:
            half = np.radians(float(cam.GetViewAngle()) * 0.5)
            scale = dist * float(np.tan(half))
            if scale > _EPS:
                cam.SetParallelScale(scale)
        else:
            scale = float(cam.GetParallelScale())
            angle = 2.0 * float(np.degrees(np.arctan(scale / dist)))
            cam.SetViewAngle(
                min(max(angle, _MIN_VIEW_ANGLE), _MAX_VIEW_ANGLE)
            )

    cam.SetParallelProjection(enable)
    renderer = getattr(plotter, 'renderer', None)
    if renderer is not None:
        renderer.ResetCameraClippingRange()

def apply_cam_transform(
    plotter,
    cam,
    azimuth: float = 0.0,
    elevation: float = 0.0,
    truck: float = 0.0,
    pedestal: float = 0.0,
    dolly: float = 0.0,
) -> None:
    if all(abs(v) < _EPS for v in
           (azimuth, elevation, truck, pedestal, dolly)):
        return

    if abs(azimuth) > _EPS:
        cam.Azimuth(azimuth)
    if abs(elevation) > _EPS:

        cam_rotate_x_rodrigues(plotter, cam, -elevation)

    base = getattr(plotter, '_init_focal_dist', 0.0)
    if base <= _EPS:
        base = cam.GetDistance()

    _, up, right = _cam_basis(cam)
    if abs(truck) > _EPS:
        _shift_cam(cam, right * base * truck, True)
    if abs(pedestal) > _EPS:
        _shift_cam(cam, up * base * pedestal, True)
    if abs(dolly) > _EPS:
        fwd, _, _ = _cam_basis(cam)
        _shift_cam(cam, fwd * base * dolly, False)

    plotter.renderer.ResetCameraClippingRange()

def get_cam_transform(plotter) -> tuple:
    renderer = getattr(plotter, 'renderer', None)
    if renderer is None:
        return (0.0, 0.0, 0.0, 0.0, 0.0)

    cam = renderer.GetActiveCamera()
    pos = np.array(cam.GetPosition(), dtype=float)
    focal = np.array(cam.GetFocalPoint(), dtype=float)
    arm = pos - focal
    dist = float(np.linalg.norm(arm))
    if dist < _EPS:
        return (0.0, 0.0, 0.0, 0.0, 0.0)

    azimuth = float(np.degrees(np.arctan2(arm[0], arm[2])))
    elevation = float(
        np.degrees(np.arcsin(np.clip(arm[1] / dist, -1.0, 1.0)))
    )

    base = getattr(plotter, '_init_focal_dist', 0.0)
    center = getattr(plotter, '_norm_center', None)
    if base <= _EPS or center is None:
        return (azimuth, elevation, 0.0, 0.0, 0.0)

    _, up, right = _cam_basis(cam)
    off = focal - np.array(center, dtype=float)
    truck = float(np.dot(off, right) / base)
    pedestal = float(np.dot(off, up) / base)
    dolly = float((base - dist) / base)
    return (azimuth, elevation, truck, pedestal, dolly)

def restore_initial_camera(plotter) -> None:
    if hasattr(plotter, '_init_cam_pos'):
        plotter.camera_position = plotter._init_cam_pos
    cam = plotter.renderer.GetActiveCamera()

    if hasattr(plotter, '_init_parallel_proj'):
        set_parallel_projection(plotter, cam, plotter._init_parallel_proj)
    if hasattr(plotter, '_init_parallel_scale'):
        cam.SetParallelScale(plotter._init_parallel_scale)
    if hasattr(plotter, '_init_view_angle'):
        cam.SetViewAngle(plotter._init_view_angle)
    plotter._rot_elev = 0.0
    plotter._current_view = None
    plotter.renderer.ResetCameraClippingRange()
