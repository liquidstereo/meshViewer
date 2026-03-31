import logging
import numpy as np
import vtk
from vtk.util.numpy_support import numpy_to_vtk

from configs.defaults import FNORMAL_SPATIAL_INTERVAL
from process.mode.common import _get_cam_dir

logger = logging.getLogger(__name__)

def apply_face_normal(p, mesh):
    fnormal_axis = getattr(p, '_fnormal_axis', 3)

    prev_src = getattr(p, '_cached_fnormal_src', None)
    prev_axis = getattr(p, '_cached_fnormal_axis', -1)

    if prev_src is mesh and fnormal_axis == prev_axis:

        p._fnormal_actor.VisibilityOn()
        return

    s = getattr(p, '_norm_scale', 1.0)
    c = np.array(getattr(p, '_norm_center', [0.0, 0.0, 0.0]))

    centers = mesh.cell_centers().points
    if 'Normals' not in mesh.cell_data:
        tmp = mesh.copy()
        tmp.compute_normals(
            cell_normals=True, point_normals=False, inplace=True,
        )
        normals = tmp.cell_data['Normals']
    else:
        normals = mesh.cell_data['Normals']

    world_centers = s * centers + (1.0 - s) * c

    grid_cells = np.floor(
        world_centers / FNORMAL_SPATIAL_INTERVAL
    ).astype(np.int64)
    _, first_occ = np.unique(grid_cells, axis=0, return_index=True)
    indices = np.sort(first_occ)

    sel_normals = normals[indices]

    vtk_pts = vtk.vtkPoints()
    vtk_pts.SetData(
        numpy_to_vtk(world_centers[indices], deep=True)
    )
    vtk_n = numpy_to_vtk(sel_normals, deep=True)
    vtk_n.SetName('Normals')

    if fnormal_axis == 3:
        cam_dir = _get_cam_dir(p)
        scalar_data = -(sel_normals @ cam_dir).astype(np.float32)
    else:
        scalar_data = sel_normals[:, fnormal_axis].astype(np.float32)
    vtk_scalar = numpy_to_vtk(scalar_data, deep=True)
    vtk_scalar.SetName('FlowScalar')

    poly = getattr(p, '_fnormal_poly', None)
    if poly is None:
        poly = vtk.vtkPolyData()
        p._fnormal_poly = poly

    poly.SetPoints(vtk_pts)
    poly.GetPointData().SetNormals(vtk_n)
    poly.GetPointData().SetScalars(vtk_scalar)
    poly.Modified()

    p._fnormal_glyph.SetInputData(poly)
    p._fnormal_glyph.Update()
    p._fnormal_actor.VisibilityOn()

    p._cached_fnormal_src = mesh
    p._cached_fnormal_axis = fnormal_axis
