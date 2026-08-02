import logging

import numpy as np
import vtk
from vtkmodules.util.numpy_support import vtk_to_numpy

from configs.settings import (
    ID_COLOR_PALETTE, DEFAULT_ID_SHADER,
    PBR_METALLIC, PBR_ROUGHNESS, PBR_ANISOTROPY,
)
from process.mode.common import (
    _set_mesh_input, _set_scalars_buffer, _set_normals_buffer,
)
from process.plotter.state import resolve_id_shader, resolve_id_style

logger = logging.getLogger(__name__)

_ARR_NAME = 'IdColor'
_REGION_ARR = 'RegionId'
_STYLE_FLAT = 0
_SHADER_SMOOTH = 'smooth'
_SHADER_PBR = 'pbr'

def _hex_to_rgb(value: str) -> tuple:
    text = value.lstrip('#')
    return (
        int(text[0:2], 16), int(text[2:4], 16), int(text[4:6], 16),
    )

def _build_palette() -> np.ndarray:
    return np.array(
        [_hex_to_rgb(c) for c in ID_COLOR_PALETTE], dtype=np.uint8,
    )

_PALETTE = _build_palette()

def _compute_region_ids(mesh):
    conn = vtk.vtkPolyDataConnectivityFilter()
    conn.SetInputData(mesh)
    conn.SetExtractionModeToAllRegions()
    conn.ColorRegionsOn()
    conn.Update()

    out = conn.GetOutput()
    arr = out.GetPointData().GetArray(_REGION_ARR)
    if arr is None or out.GetNumberOfPoints() != mesh.n_points:
        logger.warning(
            'ID.COLOR: connectivity output mismatch'
            ' (%s points vs %s); falling back to a single color.',
            out.GetNumberOfPoints() if arr is not None else 'no RegionId',
            mesh.n_points,
        )
        return None
    return np.array(vtk_to_numpy(arr), dtype=np.int64, copy=True)

def _resolve_colors(p, mesh) -> np.ndarray:
    key = (mesh.n_points, mesh.n_faces_strict)
    if getattr(p, '_id_region_key', None) == key:
        return p._id_colors

    ids = _compute_region_ids(mesh)
    if ids is None:
        colors = np.repeat(
            _PALETTE[0][None, :], mesh.n_points, axis=0,
        )
        count = 0
    else:
        colors = _PALETTE[ids % len(_PALETTE)]
        count = int(ids.max()) + 1 if ids.size else 0

    p._id_region_key = key
    p._id_colors = np.ascontiguousarray(colors, dtype=np.uint8)
    p._id_region_count = count
    logger.info(
        'ID.COLOR: %d regions (%d points, palette %d)',
        count, mesh.n_points, len(_PALETTE),
    )
    return p._id_colors

def _resolve_style(p) -> tuple:
    style = resolve_id_style(getattr(p, '_id_style', None))
    return style, resolve_id_shader(DEFAULT_ID_SHADER)

def _needs_normals(p, shader: str) -> bool:

    if shader == _SHADER_SMOOTH or shader == _SHADER_PBR:
        return True
    return getattr(p, '_is_smooth_shading', False)

def _apply_shading(prop, lit: bool, smooth: bool, shader: str) -> None:
    if lit and shader == _SHADER_PBR:
        prop.SetInterpolationToPBR()
        prop.SetMetallic(PBR_METALLIC)
        prop.SetRoughness(PBR_ROUGHNESS)
        prop.SetAnisotropy(PBR_ANISOTROPY)
        return
    if smooth:
        prop.SetInterpolationToPhong()
    else:
        prop.SetInterpolationToFlat()

def apply_id_color(p, mesh) -> None:
    colors = _resolve_colors(p, mesh)

    mapper = p._mesh_mapper
    actor = p._mesh_actor

    style, shader = _resolve_style(p)
    lit = style != _STYLE_FLAT
    smooth = lit and _needs_normals(p, shader)
    cached = _set_mesh_input(mapper, mesh, p, '_cached_mesh_poly')

    if smooth:
        if 'Normals' not in mesh.point_data:
            mesh.compute_normals(inplace=True)
        _set_normals_buffer(
            cached, mesh.point_data['Normals'], p, '_mesh_normal_buf',
        )
    else:
        cached.GetPointData().SetNormals(None)
        cached.GetPointData().Modified()
    _set_scalars_buffer(
        cached, colors, _ARR_NAME, p, '_mesh_id_buf',
        array_type=vtk.VTK_UNSIGNED_CHAR,
    )

    mapper.SetScalarModeToDefault()
    mapper.SetColorModeToDirectScalars()
    mapper.ScalarVisibilityOn()
    actor.SetTexture(None)

    prop = actor.GetProperty()
    prop.SetOpacity(getattr(p, '_mesh_opacity', 1.0))
    prop.SetLighting(lit)
    prop.SetRepresentationToSurface()
    prop.EdgeVisibilityOff()
    _apply_shading(prop, lit, smooth, shader)
    if getattr(p, '_is_backface', True):
        prop.BackfaceCullingOn()
    else:
        prop.BackfaceCullingOff()

    actor.VisibilityOn()
    p._prev_mode = 'id_color'
