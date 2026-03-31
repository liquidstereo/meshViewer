import logging

import numpy as np
import vtk
from vtk.util.numpy_support import numpy_to_vtk

from configs.defaults import MESH_QUALITY_METRIC

logger = logging.getLogger(__name__)

_QUALITY_ARR = '_MQ'

def apply_mesh_quality(p, mesh):
    n_faces = mesh.n_faces_strict
    if p._quality_cache is None or p._quality_cache_n_faces != n_faces:
        _rebuild_quality_cache(p, mesh, n_faces)

    poly = p._quality_vtk_poly
    poly.SetPoints(mesh.GetPoints())
    poly.SetPolys(mesh.GetPolys())
    poly.Modified()

    q_range = p._quality_cache_range
    mapper = p._mesh_mapper
    actor = p._mesh_actor

    mapper.SetInputData(poly)
    mapper.SetColorModeToMapScalars()
    mapper.SetScalarModeToUseCellData()
    mapper.SelectColorArray(_QUALITY_ARR)
    mapper.ScalarVisibilityOn()
    mapper.SetLookupTable(p._quality_lut)
    mapper.SetScalarRange(*q_range)
    p._cmap_lut = p._quality_lut
    p._cmap_range = q_range
    p._cmap_title = 'QUALITY'

    actor.SetTexture(None)
    prop = actor.GetProperty()
    prop.SetOpacity(1.0)
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
    p._prev_mode = 'mesh_quality'

def _rebuild_quality_cache(p, mesh, n_faces: int) -> None:
    quality_mesh = mesh.cell_quality(quality_measure=MESH_QUALITY_METRIC)

    q_arr = None
    for v in quality_mesh.cell_data.values():
        if v.ndim == 1 and len(v) == n_faces:
            q_arr = v
            break
    if q_arr is None:
        q_arr = quality_mesh.active_scalars

    q_np = np.asarray(q_arr, dtype=np.float32)
    q_range = (float(q_np.min()), float(q_np.max()))

    vtk_arr = numpy_to_vtk(q_np, deep=True, array_type=vtk.VTK_FLOAT)
    vtk_arr.SetName(_QUALITY_ARR)

    quality_poly = vtk.vtkPolyData()
    quality_poly.GetCellData().AddArray(vtk_arr)
    quality_poly.GetCellData().SetActiveScalars(_QUALITY_ARR)

    p._quality_cache = q_np
    p._quality_cache_n_faces = n_faces
    p._quality_cache_range = q_range
    p._quality_vtk_poly = quality_poly
    logger.debug('mesh_quality: cache miss, n_faces=%d', n_faces)
