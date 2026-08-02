import logging

import vtk

from configs.settings import (
    OFFSET_MESH_BACK,
    OUTLINE_BORDER_EDGES, OUTLINE_FEATURE_ANGLE, OUTLINE_FEATURE_ENABLE,
)
from process.mode.common import (
    _set_mesh_input, _set_scalars_buffer,
    _set_flat_line_lighting, _set_actor_transform,
)
from process.mode.id_color import _resolve_colors
from process.mode.surface import apply_normal

logger = logging.getLogger(__name__)

_ARR_NAME = 'OutlineIdColor'

def _sync_silhouette(p, mesh):
    sil = p._outline_sil
    _set_mesh_input(sil, mesh, p, '_cached_outline_poly')
    sil.SetBorderEdges(int(OUTLINE_BORDER_EDGES))
    sil.SetEnableFeatureAngle(int(OUTLINE_FEATURE_ENABLE))
    sil.SetFeatureAngle(OUTLINE_FEATURE_ANGLE)
    sil.Update()
    return sil.GetOutput()

def _sync_outline_poly(p, out):
    poly = getattr(p, '_outline_poly', None)
    if poly is None:
        poly = vtk.vtkPolyData()
        p._outline_poly = poly
    pts = out.GetPoints()
    if poly.GetPoints() is not pts:
        poly.SetPoints(pts)
    poly.SetLines(out.GetLines())
    poly.Modified()
    return poly

def apply_outline(p, mesh) -> None:
    colors = _resolve_colors(p, mesh)
    out = _sync_silhouette(p, mesh)
    poly = _sync_outline_poly(p, out)
    _set_scalars_buffer(
        poly, colors, _ARR_NAME, p, '_outline_color_buf',
        array_type=vtk.VTK_UNSIGNED_CHAR,
    )

    mapper = p._outline_mapper
    mapper.SetInputData(poly)
    mapper.SetScalarModeToUsePointData()
    mapper.SetColorModeToDirectScalars()
    mapper.ScalarVisibilityOn()

    actor = p._outline_actor
    _set_flat_line_lighting(actor.GetProperty())
    _set_actor_transform(actor, p)
    actor.VisibilityOn()
    logger.debug(
        'apply_outline: %d lines (%d regions)',
        poly.GetNumberOfLines(), getattr(p, '_id_region_count', 0),
    )

def apply_outline_body(p, mesh, preloaded_tex) -> None:
    if getattr(p, '_outline_mesh_hidden', True):
        p._mesh_actor.VisibilityOff()
        p._prev_mode = 'outline_body'
        return
    apply_normal(p, mesh, preloaded_tex)
    p._mesh_mapper.SetResolveCoincidentTopologyToPolygonOffset()
    p._mesh_mapper.SetRelativeCoincidentTopologyPolygonOffsetParameters(
        *OFFSET_MESH_BACK
    )
    p._mesh_actor.VisibilityOn()
    p._prev_mode = 'outline_body'
