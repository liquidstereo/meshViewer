import logging

import numpy as np
import vtk as _vtk
import matplotlib.cm as _cm
from vtk.util.numpy_support import numpy_to_vtk

from configs.defaults import (
    POINT_FOG_START,
    PT_CLOUD_SIZE_DEFAULT,
    PT_CLOUD_SHADER_SCALE,
    PT_CLOUD_SHADER_SIZE_MIN,
    PT_CLOUD_SHADER_SIZE_MAX,
    PT_CLOUD_DEPTH_CONTRAST,
    COLOR_PT_CLOUD_DEPTH,
    RENDER_MSAA_SAMPLES,
    SAVE_ALPHA,
)
from process.mode.surface import _pack_vertex_colors
from process.mode.depth import _compute_depth, _compute_bbox_depth_range
from process.mode.common import _set_mesh_input
from process.mode.labels import AXIS_NAMES

logger = logging.getLogger(__name__)

def set_pc_render_quality(p, is_pc: bool) -> None:
    if SAVE_ALPHA:
        return
    rw = p.render_window
    target = 0 if is_pc else RENDER_MSAA_SAMPLES
    if rw.GetMultiSamples() != target:
        rw.SetMultiSamples(target)
        label = 'PC: MSAA -> 0' if is_pc else f'mesh: MSAA -> {target}'
        logger.debug('set_pc_render_quality: %s', label)

def inject_pt_size_shader(actor, base_size: float) -> bool:
    scale = PT_CLOUD_SHADER_SCALE * base_size
    size_max = PT_CLOUD_SHADER_SIZE_MAX * base_size
    code = (
        '  float _ptDist = max(gl_Position.w, 0.001);\n'
        f'  gl_PointSize = clamp({scale:.2f} / _ptDist,'
        f' {PT_CLOUD_SHADER_SIZE_MIN:.2f}, {size_max:.2f});\n'
    )
    try:
        sp = actor.GetShaderProperty()
        sp.AddVertexShaderReplacement(
            '//VTK::PositionVC::Impl',
            False,
            code,
            False,
        )
        return True
    except Exception as e:
        logger.warning('pt size shader injection failed: %s', e)
        return False

def inject_pt_fog_shader(actor, base_size: float) -> bool:
    scale = PT_CLOUD_SHADER_SCALE * base_size
    size_max = PT_CLOUD_SHADER_SIZE_MAX * base_size
    vert_impl = (
        '  float _ptDist = max(gl_Position.w, 0.001);\n'
        f'  gl_PointSize = clamp({scale:.2f} / _ptDist,'
        f' {PT_CLOUD_SHADER_SIZE_MIN:.2f}, {size_max:.2f});\n'
    )

    frag_code = (
        '//VTK::System::Dec\n'
        'out vec4 fragOutput0;\n'
        'in vec4 vertexColorVSOutput;\n'
        'uniform float u_near;\n'
        'uniform float u_far;\n'
        'uniform float u_dmin;\n'
        'uniform float u_dmax;\n'
        'uniform float u_bg_r;\n'
        'uniform float u_bg_g;\n'
        'uniform float u_bg_b;\n'
        'void main() {\n'
        '  float _linear = u_near * u_far / max(\n'
        '    u_far - gl_FragCoord.z * (u_far - u_near), 0.001);\n'
        '  float _cpu_d = -_linear;\n'
        '  float _span = max(u_dmax - u_dmin, 0.001);\n'
        '  float _dn = clamp((_cpu_d - u_dmin) / _span, 0.0, 1.0);\n'
        f'  float _dc = clamp(0.5 + (_dn - 0.5)'
        f' * {PT_CLOUD_DEPTH_CONTRAST:.4f}, 0.0, 1.0);\n'
        '  float _dist = 1.0 - _dc;\n'
        f'  float _tail = max(1.0 - {POINT_FOG_START:.4f}, 0.00001);\n'
        f'  float _fog_t = clamp((_dist - {POINT_FOG_START:.4f})'
        f' / _tail, 0.0, 1.0);\n'
        '  vec3 _base = vertexColorVSOutput.rgb;\n'
        '  fragOutput0 = vec4(\n'
        '    mix(_base, vec3(u_bg_r, u_bg_g, u_bg_b), _fog_t), 1.0);\n'
        '}\n'
    )
    try:
        sp = actor.GetShaderProperty()
        try:
            sp.ClearAllVertexShaderReplacements()
        except AttributeError:
            pass
        sp.AddVertexShaderReplacement(
            '//VTK::PositionVC::Impl', False, vert_impl, False,
        )
        sp.SetFragmentShaderCode(frag_code)
        return True
    except Exception as e:
        logger.warning('pt fog shader injection failed: %s', e)
        return False

def _update_pt_fog_uniforms(
    sp, d_min: float, d_max: float, bg: tuple,
    near: float, far: float,
) -> None:
    vu = sp.GetFragmentCustomUniforms()
    vu.SetUniformf('u_dmin', d_min)
    vu.SetUniformf('u_dmax', d_max)
    vu.SetUniformf('u_bg_r', bg[0])
    vu.SetUniformf('u_bg_g', bg[1])
    vu.SetUniformf('u_bg_b', bg[2])
    vu.SetUniformf('u_near', near)
    vu.SetUniformf('u_far', far)

def _apply_pt_fog_gpu(
    p, mesh, mapper, actor, base_size: float, use_rgb: bool,
) -> None:
    d_min, d_max = _compute_bbox_depth_range(p, mesh)
    bg = tuple(p.renderer.GetBackground())
    cam = p.renderer.GetActiveCamera()
    near, far = cam.GetClippingRange()
    _unif_key = (
        round(d_min, 1), round(d_max, 1), bg,
        round(near, 3), round(far, 1),
    )
    if getattr(p, '_pt_fog_unif_key', None) != _unif_key:
        try:
            _update_pt_fog_uniforms(
                actor.GetShaderProperty(), d_min, d_max, bg, near, far,
            )
            p._pt_fog_unif_key = _unif_key
        except Exception as e:
            logger.warning('pt fog uniform update failed: %s', e)
            p._pt_fog_gpu = False
            return

    _color_key = (id(mesh), use_rgb)
    if getattr(p, '_pt_fog_color_key', None) != _color_key:
        if use_rgb:
            raw = _pack_vertex_colors(mesh)
            if raw is None:
                raw = np.full(
                    (mesh.n_points, 3), 255, dtype=np.uint8,
                )
        else:
            raw = np.full((mesh.n_points, 3), 255, dtype=np.uint8)
        cached = _set_mesh_input(mapper, mesh, p, '_cached_mesh_poly')
        p._pt_color_buf = raw
        vtk_c = numpy_to_vtk(
            raw, deep=False, array_type=_vtk.VTK_UNSIGNED_CHAR,
        )
        vtk_c.SetName('PtFogColors')
        cached.GetPointData().SetScalars(vtk_c)
        cached.GetPointData().Modified()
        p._pt_fog_color_key = _color_key
    mapper.ScalarVisibilityOn()
    mapper.SetColorModeToDirectScalars()
    actor.SetTexture(None)
    prop = actor.GetProperty()
    prop.SetOpacity(1.0)
    prop.SetLighting(False)
    prop.SetRepresentationToSurface()
    prop.EdgeVisibilityOff()
    prop.SetPointSize(base_size)
    prop.SetInterpolationToFlat()
    actor.VisibilityOn()
    p._prev_mode = 'pt_fog'

def build_pt_fog_lut(p, cmap_name: str) -> np.ndarray:
    bg = tuple(p.renderer.GetBackground())
    key = (cmap_name, bg)
    if getattr(p, '_pt_fog_lut_key', None) == key:
        return p._pt_fog_lut_cache
    t_vals = np.linspace(0, 1, 256, dtype=np.float32)
    colors = _cm.get_cmap(cmap_name)(t_vals)[:, :3].astype(np.float32)
    bg_arr = np.array(bg, dtype=np.float32)
    depth_dist = 1.0 - t_vals
    _tail = max(1.0 - POINT_FOG_START, 1e-6)
    fog_t = np.clip(
        (depth_dist - POINT_FOG_START) / _tail, 0.0, 1.0,
    )[:, np.newaxis]
    lut = (
        (colors * (1.0 - fog_t) + bg_arr * fog_t) * 255
    ).astype(np.uint8)
    p._pt_fog_lut_cache = lut
    p._pt_fog_lut_key = key
    return lut

def pt_cam_key(p, mesh) -> tuple:
    cam = p.renderer.GetActiveCamera()
    d = cam.GetDirectionOfProjection()
    pos = cam.GetPosition()
    return (
        id(mesh),
        round(d[0], 5), round(d[1], 5), round(d[2], 5),
        round(pos[0], 4), round(pos[1], 4), round(pos[2], 4),
        tuple(p.renderer.GetBackground()),
    )

def apply_pt_normal(p, mesh) -> None:
    _base = getattr(p, '_pt_cloud_size', PT_CLOUD_SIZE_DEFAULT)
    use_rgb = getattr(p, '_pt_cloud_use_rgb', True)
    mapper = p._mesh_mapper
    actor = p._mesh_actor

    _shader_size = getattr(p, '_pt_shader_size', -1)
    if _shader_size != _base and _shader_size != 0:
        ok = inject_pt_size_shader(actor, _base)
        p._pt_shader_size = _base if ok else 0

    _color_key = (id(mesh), use_rgb)
    if getattr(p, '_pt_normal_color_key', None) == _color_key:
        return
    p._pt_normal_color_key = _color_key

    cached = _set_mesh_input(mapper, mesh, p, '_cached_mesh_poly')
    if use_rgb:
        raw = _pack_vertex_colors(mesh)
        if raw is None:
            raw = np.full((mesh.n_points, 3), 255, dtype=np.uint8)
    else:
        raw = np.full((mesh.n_points, 3), 255, dtype=np.uint8)
    p._pt_color_buf = raw
    vtk_c = numpy_to_vtk(raw, deep=False, array_type=_vtk.VTK_UNSIGNED_CHAR)
    vtk_c.SetName('PtNormalColors')
    cached.GetPointData().SetScalars(vtk_c)
    cached.GetPointData().Modified()
    mapper.ScalarVisibilityOn()
    mapper.SetColorModeToDirectScalars()
    actor.SetTexture(None)
    prop = actor.GetProperty()
    prop.SetOpacity(1.0)
    prop.SetLighting(False)
    prop.SetRepresentationToSurface()
    prop.EdgeVisibilityOff()
    prop.SetPointSize(_base)
    prop.SetInterpolationToFlat()
    actor.VisibilityOn()
    p._prev_mode = 'pt_normal'

def apply_pt_depth(p, mesh) -> None:
    _base = getattr(p, '_pt_cloud_size', PT_CLOUD_SIZE_DEFAULT)
    _shader_size = getattr(p, '_pt_shader_size', -1)
    if _shader_size != _base and _shader_size != 0:
        ok = inject_pt_size_shader(p._mesh_actor, _base)
        p._pt_shader_size = _base if ok else 0

    _key = pt_cam_key(p, mesh)
    if getattr(p, '_pt_depth_cache_key', None) == _key:
        return
    p._pt_depth_cache_key = _key

    mapper = p._mesh_mapper
    actor = p._mesh_actor
    lut = getattr(p, '_pt_depth_lut', None)
    if lut is None:
        from process.mode.surface import apply_normal
        apply_normal(p, mesh, None)
        return

    saved_axis = getattr(p, '_depth_axis', 3)
    p._depth_axis = 3
    depth = _compute_depth(p, mesh)
    p._depth_axis = saved_axis

    d_min, d_max = float(depth.min()), float(depth.max())
    span = d_max - d_min
    if span > 1e-12:
        depth_n = (depth - d_min) / span
        depth_n = np.clip(
            0.5 + (depth_n - 0.5) * PT_CLOUD_DEPTH_CONTRAST,
            0.0, 1.0,
        ).astype(np.float32)
    else:
        depth_n = np.zeros_like(depth, dtype=np.float32)

    fog_lut = build_pt_fog_lut(p, COLOR_PT_CLOUD_DEPTH)
    idx = (depth_n * 255.0).clip(0, 255).astype(np.uint8)
    blended = fog_lut[idx]

    cached = _set_mesh_input(mapper, mesh, p, '_cached_mesh_poly')
    p._pt_color_buf = blended
    vtk_c = numpy_to_vtk(
        blended, deep=False, array_type=_vtk.VTK_UNSIGNED_CHAR,
    )
    vtk_c.SetName('PtDepthColors')
    cached.GetPointData().SetScalars(vtk_c)
    cached.GetPointData().Modified()
    mapper.ScalarVisibilityOn()
    mapper.SetColorModeToDirectScalars()

    p._cmap_lut = lut
    p._cmap_range = (0.0, 1.0)
    p._cmap_title = f'DEPTH.{AXIS_NAMES[3]}'
    actor.SetTexture(None)
    prop = actor.GetProperty()
    prop.SetOpacity(1.0)
    prop.SetLighting(False)
    prop.SetRepresentationToSurface()
    prop.EdgeVisibilityOff()
    prop.SetPointSize(getattr(p, '_pt_cloud_size', 1))
    prop.SetInterpolationToFlat()
    actor.VisibilityOn()
    p._prev_mode = 'pt_depth'

def apply_pt_fog(p, mesh) -> None:
    _base = getattr(p, '_pt_cloud_size', PT_CLOUD_SIZE_DEFAULT)
    use_rgb = getattr(p, '_pt_cloud_use_rgb', False)
    use_depth_cmap = getattr(p, '_pt_cloud_depth', False)
    mapper = p._mesh_mapper
    actor = p._mesh_actor

    if not use_depth_cmap:
        _fog_gpu = getattr(p, '_pt_fog_gpu', None)
        _fog_gpu_base = getattr(p, '_pt_fog_gpu_base', -1)
        if _fog_gpu is None or _fog_gpu_base != _base:
            ok = inject_pt_fog_shader(actor, _base)
            p._pt_fog_gpu = ok
            p._pt_fog_gpu_base = _base
            _fog_gpu = ok
        if _fog_gpu:
            _apply_pt_fog_gpu(p, mesh, mapper, actor, _base, use_rgb)
            return

    _shader_size = getattr(p, '_pt_shader_size', -1)
    if _shader_size != _base and _shader_size != 0:
        ok = inject_pt_size_shader(actor, _base)
        p._pt_shader_size = _base if ok else 0

    _key = (pt_cam_key(p, mesh), use_rgb, use_depth_cmap)
    if getattr(p, '_pt_fog_cache_key', None) == _key:
        return
    p._pt_fog_cache_key = _key

    saved_axis = getattr(p, '_depth_axis', 3)
    p._depth_axis = 3
    depth = _compute_depth(p, mesh)
    p._depth_axis = saved_axis

    span = float(depth.max() - depth.min())
    if span > 1e-12:
        depth_n = ((depth - depth.min()) / span).astype(np.float32)
        depth_n = np.clip(
            0.5 + (depth_n - 0.5) * PT_CLOUD_DEPTH_CONTRAST,
            0.0, 1.0,
        )
    else:
        depth_n = np.zeros(mesh.n_points, dtype=np.float32)

    bg_arr = np.array(p.renderer.GetBackground(), dtype=np.float32)

    if use_depth_cmap:
        fog_lut = build_pt_fog_lut(p, COLOR_PT_CLOUD_DEPTH)
        idx = (depth_n * 255.0).clip(0, 255).astype(np.uint8)
        blended = fog_lut[idx]
    else:
        if use_rgb:
            base_u8 = _pack_vertex_colors(mesh)
            base = (
                base_u8.astype(np.float32) / 255.0
                if base_u8 is not None
                else np.ones((mesh.n_points, 3), dtype=np.float32)
            )
        else:
            base = np.ones((mesh.n_points, 3), dtype=np.float32)
        depth_dist = 1.0 - depth_n
        _tail = max(1.0 - POINT_FOG_START, 1e-6)
        t = np.clip(
            (depth_dist - POINT_FOG_START) / _tail, 0.0, 1.0,
        )[:, np.newaxis]
        blended = ((base * (1.0 - t) + bg_arr * t)
                   .clip(0.0, 1.0) * 255).astype(np.uint8)

    cached = _set_mesh_input(mapper, mesh, p, '_cached_mesh_poly')
    p._pt_color_buf = blended
    vtk_c = numpy_to_vtk(
        blended, deep=False, array_type=_vtk.VTK_UNSIGNED_CHAR,
    )
    vtk_c.SetName('PtFogColors')
    cached.GetPointData().SetScalars(vtk_c)
    cached.GetPointData().Modified()
    mapper.ScalarVisibilityOn()
    mapper.SetColorModeToDirectScalars()
    actor.SetTexture(None)
    prop = actor.GetProperty()
    prop.SetOpacity(1.0)
    prop.SetLighting(False)
    prop.SetRepresentationToSurface()
    prop.EdgeVisibilityOff()
    prop.SetPointSize(getattr(p, '_pt_cloud_size', 1))
    prop.SetInterpolationToFlat()
    actor.VisibilityOn()
    p._prev_mode = 'pt_fog'
