import logging
import numpy as np
import pyvista as pv
import vtk

from configs.settings import (
    COLOR_BG, WIDTH_ISO_LINE, TYPE_TUBE, ISO_NORMAL_OFFSET,
)
from process.mode.common import (
    _hex_to_rgb, _resolve_color, _set_mesh_input,
    _set_actor_transform, _setup_occluder_actor,
)

logger = logging.getLogger(__name__)

_CAM_DIR_TOL = 0.005

def _get_cam_dir(p) -> np.ndarray:
    cam = p.renderer.GetActiveCamera()
    d = np.array(cam.GetDirectionOfProjection())
    return d / (np.linalg.norm(d) + 1e-12)

def _get_iso_display(p, mesh):
    if getattr(p, '_cached_iso_mesh', None) is mesh:
        return p._cached_iso_display

    from configs.settings import REDUCTION_MESH
    display = mesh.copy(deep=True)
    if REDUCTION_MESH < 1.0:
        display = display.decimate(1.0 - REDUCTION_MESH)

    p._cached_iso_mesh = mesh
    p._cached_iso_display = display
    return display

def _set_flat_line_lighting(prop):
    prop.SetLighting(False)
    prop.SetInterpolationToFlat()
    prop.SetAmbient(1.0)
    prop.SetDiffuse(0.0)
    prop.SetSpecular(0.0)

def apply_isoline(p, mesh):
    iso_count = p._iso_count
    iso_axis = p._iso_axis

    display = _get_iso_display(p, mesh)

    prev_count = getattr(p, '_cached_iso_count', -1)
    prev_axis = getattr(p, '_cached_iso_axis', -1)
    prev_cam_dir = getattr(p, '_cached_iso_cam_dir', None)

    if iso_axis == 3:
        cam_dir = _get_cam_dir(p)
        same_cam = (
            prev_cam_dir is not None
            and np.linalg.norm(cam_dir - prev_cam_dir) < _CAM_DIR_TOL
        )
    else:
        cam_dir = None
        same_cam = True

    need_contour = (
        prev_count != iso_count
        or prev_axis != iso_axis
        or not same_cam
    )

    if not need_contour:
        _set_flat_line_lighting(p._iso_actor.GetProperty())
        _set_actor_transform(p._iso_actor, p)
        p._iso_actor.VisibilityOn()
        return

    if iso_axis == 3:

        display['Depth'] = -(display.points @ cam_dir)
    else:
        display['Depth'] = display.points.T[iso_axis]
    display.set_active_scalars('Depth')
    contours = display.contour(isosurfaces=iso_count)

    if ISO_NORMAL_OFFSET != 0 and contours.n_points > 0:
        if 'Normals' not in display.point_data:
            display.compute_normals(inplace=True)
        _probe = vtk.vtkProbeFilter()
        _probe.SetSourceData(display)
        _probe.SetInputData(contours)
        _probe.Update()
        _probed = pv.wrap(_probe.GetOutput())
        if 'Normals' in _probed.point_data:
            contours = _probed
            contours.points += (
                contours.point_data['Normals'] * ISO_NORMAL_OFFSET
            )

    p._iso_mapper.SetInputData(contours)
    p._iso_mapper.SetLookupTable(p._iso_lut)
    p._iso_mapper.SetScalarRange(display.get_data_range())

    prop = p._iso_actor.GetProperty()
    prop.SetLineWidth(WIDTH_ISO_LINE)
    prop.SetRenderLinesAsTubes(int(TYPE_TUBE))
    _set_flat_line_lighting(prop)

    _set_actor_transform(p._iso_actor, p)
    p._iso_actor.VisibilityOn()

    p._cached_iso_count = iso_count
    p._cached_iso_axis = iso_axis
    p._cached_iso_cam_dir = cam_dir

    p._prev_mode = 'isoline'

def apply_iso_occluder(p, mesh):
    if not getattr(p, '_is_backface', True):
        p._mesh_actor.VisibilityOff()
        p._prev_mode = 'iso_occluder'
        return
    _setup_occluder_actor(p, mesh, polygon_offset=False)
    p._prev_mode = 'iso_occluder'

def apply_iso_only(p, mesh):
    mapper = p._mesh_mapper
    actor = p._mesh_actor

    actor.SetColor(*_hex_to_rgb(COLOR_BG))

    _set_mesh_input(mapper, mesh, p, '_cached_mesh_poly')
    mapper.ScalarVisibilityOff()
    actor.SetTexture(None)

    prop = actor.GetProperty()
    prop.SetOpacity(getattr(p, '_mesh_opacity', 1.0))
    prop.SetColor(*_hex_to_rgb(COLOR_BG))
    prop.SetLighting(False)
    prop.EdgeVisibilityOff()
    prop.SetRepresentationToSurface()

    p._prev_mode = 'iso_only'
