import logging
import numpy as np
import vtk
from vtk.util.numpy_support import numpy_to_vtk, vtk_to_numpy

from configs.settings import COLOR_WIREFRAME
from process.mode.common import (
    _hex_to_rgb,
    _set_flat_line_lighting, _set_actor_transform, _setup_occluder_actor,
    _get_cam_dir,
)
from process.mode.labels import AXIS_NAMES

logger = logging.getLogger(__name__)

def _get_normals(mesh):
    if 'Normals' in mesh.point_data:
        return mesh.point_data['Normals']
    tmp = mesh.copy()
    tmp.compute_normals(inplace=True)
    return tmp.point_data['Normals']

def _compute_wire_scalars(normals, wire_axis, p):
    if wire_axis == 3:
        cam_dir = _get_cam_dir(p)
        return -(normals @ cam_dir).astype(np.float32)
    return normals[:, wire_axis].astype(np.float32)

def _update_output_scalars(out_poly, wire_axis, p):
    out_normals_vtk = out_poly.GetPointData().GetArray('_WireNormals')
    if out_normals_vtk is None:
        return
    normals = vtk_to_numpy(out_normals_vtk)
    scalars = _compute_wire_scalars(normals, wire_axis, p)
    axis_name = AXIS_NAMES[wire_axis]
    vtk_d = numpy_to_vtk(scalars, deep=True)
    vtk_d.SetName(f'WireNormal{axis_name}')
    out_poly.GetPointData().SetScalars(vtk_d)
    out_poly.GetPointData().Modified()
    out_poly.Modified()

def apply_wire(p, mesh):
    lut = getattr(p, '_wire_lut', None)
    mapper = p._wire_mapper
    actor = p._wire_actor

    last_src = getattr(p, '_cached_wire_poly_src', None)
    mesh_changed = (last_src is not mesh)

    wire_axis = getattr(p, '_wire_axis', 3)
    prev_axis = getattr(p, '_prev_wire_axis', -1)
    axis_changed = (wire_axis != prev_axis)
    is_cam_axis = (lut is not None and wire_axis == 3)

    cached = getattr(p, '_cached_wire_poly', None)
    if (cached is not None
            and cached.GetNumberOfPoints() == mesh.n_points
            and cached.GetNumberOfCells() == mesh.n_cells):
        if mesh_changed:
            cached.GetPoints().SetData(
                numpy_to_vtk(mesh.points, deep=True)
            )
            cached.GetPoints().Modified()
            cached.Modified()
    else:
        cached = vtk.vtkPolyData()
        cached.DeepCopy(mesh)
        p._cached_wire_poly = cached
        mesh_changed = True

    need_input_update = mesh_changed
    need_scalar_update = (
        lut is not None
        and not mesh_changed
        and (is_cam_axis or axis_changed)
    )

    if need_input_update:
        if lut is not None:
            normals = _get_normals(mesh)

            vtk_n = numpy_to_vtk(normals, deep=True)
            vtk_n.SetName('_WireNormals')
            cached.GetPointData().AddArray(vtk_n)
            scalars = _compute_wire_scalars(normals, wire_axis, p)
            axis_name = AXIS_NAMES[wire_axis]
            vtk_d = numpy_to_vtk(scalars, deep=True)
            vtk_d.SetName(f'WireNormal{axis_name}')
            cached.GetPointData().SetScalars(vtk_d)
            cached.GetPointData().Modified()
        mapper.SetInputData(cached)
        p._cached_wire_poly_src = mesh
    elif need_scalar_update:
        _update_output_scalars(cached, wire_axis, p)

        mapper.SetInputData(cached)

    p._prev_wire_axis = wire_axis

    if lut is not None:
        axis_name = AXIS_NAMES[wire_axis]
        mapper.ScalarVisibilityOn()
        mapper.SetLookupTable(lut)
        mapper.SetScalarRange(-1.0, 1.0)
        p._cmap_lut = lut
        p._cmap_range = (-1.0, 1.0)
        p._cmap_title = f'WIRE.{axis_name}'
    else:
        mapper.ScalarVisibilityOff()
        actor.GetProperty().SetColor(*_hex_to_rgb(COLOR_WIREFRAME))

    _set_flat_line_lighting(actor.GetProperty())
    _set_actor_transform(actor, p)
    actor.VisibilityOn()

def apply_wire_occluder(p, mesh):
    if getattr(p, '_wire_mesh_hidden', True):
        p._mesh_actor.VisibilityOff()
        p._prev_mode = 'wire_occluder'
        return
    _setup_occluder_actor(p, mesh, polygon_offset=True)
    p._prev_mode = 'wire_occluder'
