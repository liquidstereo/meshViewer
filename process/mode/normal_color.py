import logging
import numpy as np
import vtk
from vtk.util.numpy_support import numpy_to_vtk

from configs.defaults import NORMAL_COLOR_ENABLE_LIGHTING
from process.mode.common import _set_mesh_input

logger = logging.getLogger(__name__)

def apply_normal_color(p, mesh):
    if 'Normals' not in mesh.point_data:
        tmp = mesh.copy()
        tmp.compute_normals(inplace=True)
        normals = tmp.point_data['Normals']
    else:
        normals = mesh.point_data['Normals']

    colors = ((normals * 0.5 + 0.5).clip(0, 1) * 255
              ).astype(np.uint8)
    vtk_colors = numpy_to_vtk(
        colors, deep=True, array_type=vtk.VTK_UNSIGNED_CHAR,
    )
    vtk_colors.SetName('NormalColor')

    mapper = p._mesh_mapper
    actor = p._mesh_actor

    cached = _set_mesh_input(mapper, mesh, p, '_cached_mesh_poly')
    cached.GetPointData().SetScalars(vtk_colors)
    cached.GetPointData().Modified()

    mapper.SetScalarModeToDefault()
    mapper.SetColorModeToDirectScalars()
    mapper.ScalarVisibilityOn()
    actor.SetTexture(None)

    prop = actor.GetProperty()
    prop.SetOpacity(1.0)
    prop.SetLighting(NORMAL_COLOR_ENABLE_LIGHTING)
    prop.SetRepresentationToSurface()
    prop.EdgeVisibilityOff()
    is_backface = getattr(p, '_is_backface', True)
    if is_backface:
        prop.BackfaceCullingOn()
    else:
        prop.BackfaceCullingOff()

    actor.VisibilityOn()
    p._prev_mode = 'normal_color'
