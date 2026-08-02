import logging
import numpy as np
import vtk

from configs.settings import NORMAL_COLOR_ENABLE_LIGHTING
from process.mode.common import _set_mesh_input, _set_scalars_buffer

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
    mapper = p._mesh_mapper
    actor = p._mesh_actor

    cached = _set_mesh_input(mapper, mesh, p, '_cached_mesh_poly')
    _set_scalars_buffer(
        cached, colors, 'NormalColor', p, '_mesh_color_buf',
        array_type=vtk.VTK_UNSIGNED_CHAR,
    )

    mapper.SetScalarModeToDefault()
    mapper.SetColorModeToDirectScalars()
    mapper.ScalarVisibilityOn()
    actor.SetTexture(None)

    prop = actor.GetProperty()
    prop.SetOpacity(getattr(p, '_mesh_opacity', 1.0))
    prop.SetLighting(NORMAL_COLOR_ENABLE_LIGHTING)
    prop.SetRepresentationToSurface()
    prop.EdgeVisibilityOff()

    if getattr(p, '_is_smooth_shading', False):
        prop.SetInterpolationToPhong()
    else:
        prop.SetInterpolationToFlat()
    is_backface = getattr(p, '_is_backface', True)
    if is_backface:
        prop.BackfaceCullingOn()
    else:
        prop.BackfaceCullingOff()

    actor.VisibilityOn()
    p._prev_mode = 'normal_color'
