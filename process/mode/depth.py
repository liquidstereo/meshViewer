import logging
import numpy as np
from vtk.util.numpy_support import numpy_to_vtk

from configs.defaults import (
    DEPTH_SHADING_FLAT, DEPTH_ENABLE_LIGHTING, COLOR_DEPTH,
)
from process.mode.common import _hex_to_rgb, _set_mesh_input
from process.mode.labels import AXIS_NAMES

logger = logging.getLogger(__name__)

def _compute_depth(p, mesh):
    axis = getattr(p, '_depth_axis', 3)
    if axis != 3:
        return mesh.points[:, axis].astype(np.float32)
    s = getattr(p, '_norm_scale', 1.0)
    c = np.array(getattr(p, '_norm_center', [0.0, 0.0, 0.0]))
    world_pts = s * mesh.points + (1.0 - s) * c
    cam = p.renderer.GetActiveCamera()
    cam_dir = np.array(cam.GetDirectionOfProjection())
    cam_dir = cam_dir / (np.linalg.norm(cam_dir) + 1e-12)
    cam_pos = np.array(cam.GetPosition())
    return np.dot(world_pts - cam_pos, cam_dir).astype(np.float32)

def apply_depth(p, mesh):
    mapper = p._mesh_mapper
    actor = p._mesh_actor
    lut = getattr(p, '_depth_lut', None)

    if lut is not None:
        depth = _compute_depth(p, mesh)
        cached = _set_mesh_input(mapper, mesh, p, '_cached_mesh_poly')
        vtk_d = numpy_to_vtk(depth, deep=True)
        vtk_d.SetName('DepthScalar')
        cached.GetPointData().SetScalars(vtk_d)
        cached.GetPointData().Modified()
        lo, hi = float(depth.min()), float(depth.max())
        mapper.SetScalarModeToDefault()
        mapper.SetColorModeToMapScalars()
        mapper.SetLookupTable(lut)
        mapper.SetScalarRange(lo, hi)
        mapper.ScalarVisibilityOn()
        axis = getattr(p, '_depth_axis', 3)
        p._cmap_lut = lut
        p._cmap_range = (lo, hi)
        p._cmap_title = f'DEPTH.{AXIS_NAMES[axis]}'
    else:
        _set_mesh_input(mapper, mesh, p, '_cached_mesh_poly')
        mapper.ScalarVisibilityOff()

    actor.SetTexture(None)
    prop = actor.GetProperty()
    prop.SetOpacity(1.0)
    prop.SetLighting(DEPTH_ENABLE_LIGHTING)
    prop.SetRepresentationToSurface()
    prop.EdgeVisibilityOff()
    if lut is None:
        prop.SetColor(*_hex_to_rgb(COLOR_DEPTH))
    _is_smooth_shading = getattr(p, '_is_smooth_shading', False)
    if DEPTH_SHADING_FLAT and not _is_smooth_shading:
        prop.SetInterpolationToFlat()
    else:
        prop.SetInterpolationToPhong()
    is_backface = getattr(p, '_is_backface', True)
    if is_backface:
        prop.BackfaceCullingOn()
    else:
        prop.BackfaceCullingOff()

    actor.VisibilityOn()
    p._prev_mode = 'depth'
