import logging
import numpy as np
import vtk
import pyvista as pv

from configs.settings import (
    REDUCTION_MESH_QUALITY,
)
from vtk.util.numpy_support import numpy_to_vtk
from process.mode.common import _set_mesh_input

logger = logging.getLogger(__name__)

def apply_mesh_quality(p, mesh):
    q_range = (1.0, 5.0)

    if (p._prev_mode == 'mesh_quality'
            and getattr(p, '_last_mesh_for_quality', None) is mesh):
        return

    qual = mesh.cell_quality(quality_measure='aspect_ratio')
    if REDUCTION_MESH_QUALITY > 0:
        qual = qual.decimate(REDUCTION_MESH_QUALITY)

    qual = qual.cell_data_to_point_data()
    q_scalars = qual.point_data['aspect_ratio']

    mapper = p._mesh_mapper
    actor = p._mesh_actor

    cached = _set_mesh_input(mapper, qual, p, '_cached_mesh_poly')
    vtk_q = numpy_to_vtk(q_scalars, deep=True)
    vtk_q.SetName('aspect_ratio')
    cached.GetPointData().SetScalars(vtk_q)
    cached.GetPointData().Modified()

    mapper.ScalarVisibilityOn()
    mapper.SetLookupTable(p._quality_lut)
    mapper.SetScalarRange(*q_range)
    p._cmap_lut = p._quality_lut
    p._cmap_range = q_range
    p._cmap_title = 'QUALITY'

    actor.SetTexture(None)
    prop = actor.GetProperty()
    prop.SetOpacity(getattr(p, '_mesh_opacity', 1.0))
    prop.SetLighting(True)
    prop.SetRepresentationToSurface()
    prop.EdgeVisibilityOff()
    if getattr(p, '_is_smooth_shading', False):
        prop.SetInterpolationToGouraud()
    else:
        prop.SetInterpolationToFlat()
    if getattr(p, '_is_backface', True):
        prop.BackfaceCullingOn()
    else:
        prop.BackfaceCullingOff()

    actor.VisibilityOn()
    p._last_mesh_for_quality = mesh
    p._prev_mode = 'mesh_quality'
