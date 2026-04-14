import logging
import numpy as np
import vtk
from vtk.util.numpy_support import numpy_to_vtk

from configs.settings import COLOR_EDGE, EDGE_FEATURE_ANGLE
from process.mode.common import (
    _hex_to_rgb,
    _set_flat_line_lighting, _set_actor_transform, _setup_occluder_actor,
)

logger = logging.getLogger(__name__)

def apply_edge(p, mesh):
    lut = getattr(p, '_edge_lut', None)
    mapper = p._edge_mapper
    actor = p._edge_actor

    last_src = getattr(p, '_cached_edge_poly_src', None)
    mesh_changed = (last_src is not mesh)

    cached = getattr(p, '_cached_edge_poly', None)
    if (cached is not None
            and cached.GetNumberOfPoints() == mesh.n_points
            and cached.GetNumberOfCells() == mesh.n_cells):
        if mesh_changed:
            cached.GetPoints().SetData(
                numpy_to_vtk(mesh.points, deep=True)
            )
            cached.GetPoints().Modified()
    else:
        cached = vtk.vtkPolyData()
        cached.DeepCopy(mesh)
        p._cached_edge_poly = cached
        mesh_changed = True

    angle = getattr(p, '_edge_feature_angle', EDGE_FEATURE_ANGLE)
    p._edge_filter.SetFeatureAngle(angle)
    prev_angle = getattr(p, '_prev_edge_angle', None)
    angle_changed = (angle != prev_angle)

    need_filter = mesh_changed or angle_changed

    if need_filter:
        if lut is not None:
            if 'Normals' not in mesh.point_data:
                tmp = mesh.copy()
                tmp.compute_normals(inplace=True)
                normals = tmp.point_data['Normals']
            else:
                normals = mesh.point_data['Normals']
            nz = normals[:, 2].astype(np.float32)
            vtk_d = numpy_to_vtk(nz, deep=True)
            vtk_d.SetName('EdgeNormalZ')
            cached.GetPointData().SetScalars(vtk_d)
            cached.GetPointData().Modified()
        cached.Modified()
        p._edge_filter.SetInputData(cached)
        p._edge_filter.Update()

        mapper.SetInputData(p._edge_filter.GetOutput())
        p._cached_edge_poly_src = mesh
        p._prev_edge_angle = angle
        logger.debug('edge_filter.Update() executed (mesh/angle changed)')

    if lut is not None:
        mapper.ScalarVisibilityOn()
        mapper.SetLookupTable(lut)
        mapper.SetScalarRange(-1.0, 1.0)
        p._cmap_lut = lut
        p._cmap_range = (-1.0, 1.0)
        p._cmap_title = 'EDGE'
    else:
        mapper.ScalarVisibilityOff()
        actor.GetProperty().SetColor(*_hex_to_rgb(COLOR_EDGE))

    _set_flat_line_lighting(actor.GetProperty())
    _set_actor_transform(actor, p)
    actor.VisibilityOn()

def apply_edge_occluder(p, mesh):
    if (getattr(p, '_edge_mesh_hidden', True)
            or not getattr(p, '_is_backface', True)):
        p._mesh_actor.VisibilityOff()
        p._prev_mode = 'edge_occluder'
        return
    _setup_occluder_actor(p, mesh, polygon_offset=True)
    p._prev_mode = 'edge_occluder'
