import logging
import numpy as np
import vtk
from vtk.util.numpy_support import numpy_to_vtk

from configs.defaults import (
    COLOR_BG, COLOR_MESH_NO_TEX, COLOR_MESH_DEFAULT,
    PBR_METALLIC, PBR_ROUGHNESS, PBR_ANISOTROPY,
)
from process.mode.common import _set_mesh_input, _resolve_color

logger = logging.getLogger(__name__)

def _pack_vertex_colors(mesh) -> 'np.ndarray | None':
    pre = mesh.point_data.get('_rgb_packed')
    if pre is not None:
        return pre
    rgba = mesh.point_data.get('RGBA')
    if rgba is not None and rgba.ndim == 2 and rgba.shape[1] >= 3:
        return rgba[:, :3].astype(np.uint8)
    rgb = mesh.point_data.get('RGB')
    if rgb is not None and rgb.ndim == 2 and rgb.shape[1] >= 3:
        return rgb[:, :3].astype(np.uint8)
    c0 = mesh.point_data.get('COLOR_0')
    if c0 is not None and c0.ndim == 2 and c0.shape[1] >= 3:
        return (c0[:, :3] * 255).clip(0, 255).astype(np.uint8)
    r = mesh.point_data.get('red')
    g = mesh.point_data.get('green')
    b = mesh.point_data.get('blue')
    if r is not None and g is not None and b is not None:
        return np.column_stack(
            [r, g, b]
        ).astype(np.uint8)
    return None

def apply_normal(p, mesh, preloaded_tex):
    mapper = p._mesh_mapper
    actor = p._mesh_actor

    _is_smooth = getattr(p, '_is_smooth', False)
    _is_smooth_shading = getattr(p, '_is_smooth_shading', False)

    use_tex = (
        p._is_tex and not p._is_isoline
        and preloaded_tex is not None
    )
    _pbr_with_tex = getattr(p, '_pbr_with_tex', False)
    _use_pbr = (
        _pbr_with_tex
        or (_is_smooth and getattr(p, '_is_lighting', False) and not use_tex)
    )
    _need_smooth = _use_pbr or _is_smooth or _is_smooth_shading

    if (p._prev_mode is not None
            and getattr(p, '_last_mesh_for_normal', None) is mesh
            and getattr(p, '_last_tex_for_normal', None) is preloaded_tex):
        return

    cached = _set_mesh_input(mapper, mesh, p, '_cached_mesh_poly')
    if _need_smooth:
        if 'Normals' not in mesh.point_data:
            mesh.compute_normals(inplace=True)
        vtk_n = numpy_to_vtk(
            mesh.point_data['Normals'], deep=True
        )
        vtk_n.SetName('Normals')
        cached.GetPointData().SetNormals(vtk_n)
        cached.GetPointData().Modified()
    else:
        cached.GetPointData().SetNormals(None)
        cached.GetPointData().Modified()

    _use_rgb = getattr(p, '_pt_cloud_use_rgb', True)
    vtx_colors = (
        _pack_vertex_colors(mesh)
        if not use_tex and _use_rgb else None
    )
    if vtx_colors is not None:
        _is_prebaked = '_rgb_packed' in mesh.point_data
        vtk_c = numpy_to_vtk(
            vtx_colors,
            deep=not (_is_prebaked and getattr(p, '_preload_all', True)),
            array_type=vtk.VTK_UNSIGNED_CHAR,
        )
        vtk_c.SetName('VertexColors')
        cached.GetPointData().SetScalars(vtk_c)
        cached.GetPointData().Modified()
        mapper.ScalarVisibilityOn()
        mapper.SetColorModeToDirectScalars()
    else:
        if cached.GetPointData().GetScalars() is not None:
            cached.GetPointData().SetScalars(None)
            cached.GetPointData().Modified()
        mapper.ScalarVisibilityOff()
        mapper.SetColorModeToMapScalars()

    actor.VisibilityOn()
    no_tex = p._is_tex and not p._is_isoline and preloaded_tex is None
    mesh_color = (
        COLOR_BG if p._is_isoline
        else COLOR_MESH_NO_TEX if no_tex
        else COLOR_MESH_DEFAULT
    )

    prop = actor.GetProperty()
    _prev_pbr_tex = getattr(p, '_prev_pbr_tex', None)
    if use_tex and _use_pbr:
        actor.SetTexture(None)
        if preloaded_tex is not _prev_pbr_tex:
            preloaded_tex.UseSRGBColorSpaceOn()

            if hasattr(prop, 'RemoveTexture'):
                prop.RemoveTexture('albedoTex')
            prop.SetTexture('albedoTex', preloaded_tex)
            p._prev_pbr_tex = preloaded_tex
    else:
        if _prev_pbr_tex is not None:
            if hasattr(prop, 'RemoveTexture'):
                prop.RemoveTexture('albedoTex')
            else:
                prop.SetTexture('albedoTex', None)
            p._prev_pbr_tex = None
        if use_tex and preloaded_tex is not None:
            preloaded_tex.UseSRGBColorSpaceOff()
        actor.SetTexture(preloaded_tex if use_tex else None)
    actor.Modified()

    p._last_mesh_for_normal = mesh
    p._last_tex_for_normal = preloaded_tex

    is_backface = getattr(p, '_is_backface', True)
    mode_key = (
        _use_pbr, _is_smooth, _is_smooth_shading,
        is_backface, mesh_color, use_tex,
        vtx_colors is not None, _use_rgb,
    )
    if p._prev_mode == mode_key:
        return

    if vtx_colors is not None:
        logger.info(
            'Vertex colors active: %d pts (RGB from point_data)',
            len(vtx_colors),
        )
    prop.SetOpacity(1.0)
    prop.SetSpecular(0)
    prop.SetRepresentationToSurface()
    if getattr(p, '_n_faces', 1) == 0:
        prop.SetPointSize(getattr(p, '_pt_cloud_size', 1))
    prop.EdgeVisibilityOff()
    if is_backface:
        prop.BackfaceCullingOn()
    else:
        prop.BackfaceCullingOff()

    prop.SetColor(*_resolve_color(mesh_color))
    prop.SetLighting(True)
    prop.SetAmbient(0.0)
    prop.SetDiffuse(1.0)
    if _use_pbr:
        prop.SetInterpolationToPBR()
        prop.SetMetallic(PBR_METALLIC)
        prop.SetRoughness(PBR_ROUGHNESS)
        prop.SetAnisotropy(PBR_ANISOTROPY)
    elif _is_smooth or _is_smooth_shading:
        prop.SetInterpolationToPhong()
    else:
        prop.SetInterpolationToFlat()

    p._prev_mode = mode_key
