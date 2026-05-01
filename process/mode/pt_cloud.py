import logging

import numpy as np
import vtk as _vtk
import matplotlib.cm as _cm
from vtk.util.numpy_support import numpy_to_vtk

from configs.settings import (
    POINT_FOG_START,
    PT_CLOUD_SIZE_DEFAULT,
    PT_CLOUD_SHADER_SCALE,
    PT_CLOUD_SHADER_SIZE_MIN,
    PT_CLOUD_SHADER_SIZE_MAX,
    PT_CLOUD_DEPTH_CONTRAST,
    PT_CLOUD_DEPTH_COLOR,
    POINTS_COLOR,
    MESH_MATTE_COLOR,
    RENDER_MSAA_SAMPLES,
    SAVE_ALPHA,
    NP_POINT_FOG_START,
    NP_CLOUD_SIZE_DEFAULT,
    NP_CLOUD_SHADER_SCALE,
    NP_CLOUD_SHADER_SIZE_MIN,
    NP_CLOUD_SHADER_SIZE_MAX,
    NP_CLOUD_DEPTH_CONTRAST,
    NP_CLOUD_DEPTH_COLOR,
    NP_POINTS_COLOR,
)
from process.mode.surface import _pack_vertex_colors
from process.mode.common import _set_mesh_input, _hex_to_rgb
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

def inject_pt_size_shader(
    actor, base_size: float,
    shader_scale: float = PT_CLOUD_SHADER_SCALE,
    size_min: float = PT_CLOUD_SHADER_SIZE_MIN,
    size_max: float = PT_CLOUD_SHADER_SIZE_MAX,
) -> bool:
    vert_dec = (
        '//VTK::Camera::Dec\n'
        'uniform float u_ptCamDist;\n'
        'uniform float u_ptProjScale;\n'
        'uniform float u_ptBaseSize;\n'
    )

    vert_impl = (
        '  float _dist = max(u_ptCamDist, 0.001);\n'
        f'  float _scale = {shader_scale:.4f};\n'
        '  gl_PointSize = clamp((u_ptBaseSize * _scale * u_ptProjScale) / _dist,'
        f' {size_min:.2f}, {size_max:.2f} * u_ptBaseSize);\n'
    )
    try:
        sp = actor.GetShaderProperty()
        sp.AddVertexShaderReplacement('//VTK::Camera::Dec', False, vert_dec, False)
        sp.AddVertexShaderReplacement('//VTK::PositionVC::Impl', False, vert_impl, False)
        return True
    except Exception as e:
        logger.warning('pt size shader injection failed: %s', e)
        return False

def inject_pt_fog_shader(
    actor, base_size: float,
    shader_scale: float = PT_CLOUD_SHADER_SCALE,
    size_min: float = PT_CLOUD_SHADER_SIZE_MIN,
    size_max: float = PT_CLOUD_SHADER_SIZE_MAX,
    depth_contrast: float = PT_CLOUD_DEPTH_CONTRAST,
    fog_start: float = POINT_FOG_START,
) -> bool:
    vert_dec = (
        '//VTK::Camera::Dec\n'
        'uniform float u_ptCamDist;\n'
        'uniform float u_ptProjScale;\n'
        'uniform float u_ptBaseSize;\n'
    )
    vert_impl = (
        '  float _dist = max(u_ptCamDist, 0.001);\n'
        f'  float _scale = {shader_scale:.4f};\n'
        '  gl_PointSize = clamp((u_ptBaseSize * _scale * u_ptProjScale) / _dist,'
        f' {size_min:.2f}, {size_max:.2f} * u_ptBaseSize);\n'
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
        f'  float _dc = clamp(0.5 + (_dn - 0.5) * {depth_contrast:.4f}, 0.0, 1.0);\n'
        '  float _dist = 1.0 - _dc;\n'
        f'  float _tail = max(1.0 - {fog_start:.4f}, 0.00001);\n'
        f'  float _fog_t = clamp((_dist - {fog_start:.4f}) / _tail, 0.0, 1.0);\n'
        '  vec3 _base = vertexColorVSOutput.rgb;\n'
        '  fragOutput0 = vec4(\n'
        '    mix(_base, vec3(u_bg_r, u_bg_g, u_bg_b), _fog_t), 1.0);\n'
        '}\n'
    )
    try:
        sp = actor.GetShaderProperty()
        try: sp.ClearAllVertexShaderReplacements()
        except: pass
        sp.AddVertexShaderReplacement('//VTK::Camera::Dec', False, vert_dec, False)
        sp.AddVertexShaderReplacement('//VTK::PositionVC::Impl', False, vert_impl, False)
        sp.SetFragmentShaderCode(frag_code)
        return True
    except Exception as e:
        logger.warning('pt fog shader injection failed: %s', e)
        return False

def update_pt_size_uniforms(p, actor) -> None:
    try:
        cam = p.camera
        pos = np.array(cam.position)
        focal = np.array(cam.focal_point)
        _sz_def = (
            NP_CLOUD_SIZE_DEFAULT
            if getattr(p, '_is_np_data', False)
            else PT_CLOUD_SIZE_DEFAULT
        )
        base_size = float(getattr(p, '_pt_cloud_size', _sz_def))

        cam_dist = float(np.linalg.norm(pos - focal))

        if cam.GetParallelProjection():
            proj_scale = 1.0 / max(cam.GetParallelScale(), 0.0001)
            cam_dist = 1.0
        else:
            fov_rad = np.radians(cam.GetViewAngle())
            proj_scale = 1.0 / np.tan(fov_rad / 2.0)

        sp = actor.GetShaderProperty()
        vu = sp.GetVertexCustomUniforms()
        vu.SetUniformf('u_ptCamDist', cam_dist)
        vu.SetUniformf('u_ptProjScale', proj_scale)
        vu.SetUniformf('u_ptBaseSize', base_size)

        _key = (round(cam_dist, 3), round(proj_scale, 5), base_size)
        if getattr(p, '_pt_size_unif_key', None) != _key:
            p._pt_size_unif_key = _key
            actor.GetMapper().Modified()

    except Exception as e:
        logger.debug('update_pt_size_uniforms failed: %s', e)

def _update_pt_fog_uniforms(sp, d_min: float, d_max: float, bg: tuple, near: float, far: float) -> None:
    vu = sp.GetFragmentCustomUniforms()
    vu.SetUniformf('u_dmin', d_min); vu.SetUniformf('u_dmax', d_max)
    vu.SetUniformf('u_bg_r', bg[0]); vu.SetUniformf('u_bg_g', bg[1]); vu.SetUniformf('u_bg_b', bg[2])
    vu.SetUniformf('u_near', near); vu.SetUniformf('u_far', far)

def _apply_pt_fog_gpu(p, mesh, mapper, actor, base_size: float, use_rgb: bool) -> None:
    from process.mode.depth import _compute_bbox_depth_range
    d_min, d_max = _compute_bbox_depth_range(p, mesh)
    bg = tuple(p.renderer.GetBackground())
    cam = p.renderer.GetActiveCamera()
    near, far = cam.GetClippingRange()
    _unif_key = (round(d_min, 1), round(d_max, 1), bg, round(near, 3), round(far, 1))
    if getattr(p, '_pt_fog_unif_key', None) != _unif_key:
        try:
            _update_pt_fog_uniforms(actor.GetShaderProperty(), d_min, d_max, bg, near, far)
            p._pt_fog_unif_key = _unif_key
        except Exception as e:
            logger.warning('pt fog uniform update failed: %s', e)
            p._pt_fog_gpu = False; return

    _color_key = (id(mesh), use_rgb)
    if getattr(p, '_pt_fog_color_key', None) != _color_key:
        raw = _pack_vertex_colors(mesh) if use_rgb else None
        if raw is None:
            _pc = (
                NP_POINTS_COLOR
                if getattr(p, '_is_np_data', False)
                else POINTS_COLOR
            )
            c = [int(v * 255) for v in _hex_to_rgb(_pc)]
            raw = np.full((mesh.n_points, 3), c, dtype=np.uint8)
        cached = _set_mesh_input(mapper, mesh, p, '_cached_mesh_poly')
        p._pt_color_buf = raw
        vtk_c = numpy_to_vtk(raw, deep=False, array_type=_vtk.VTK_UNSIGNED_CHAR)
        vtk_c.SetName('PtFogColors')
        cached.GetPointData().SetScalars(vtk_c)
        cached.GetPointData().Modified()
        p._pt_fog_color_key = _color_key
    mapper.ScalarVisibilityOn()
    mapper.SetColorModeToDirectScalars()
    actor.SetTexture(None)
    _opacity = getattr(p, '_mesh_opacity', 1.0)
    prop = actor.GetProperty()
    prop.SetOpacity(_opacity); prop.SetLighting(False)
    prop.SetRepresentationToSurface(); prop.EdgeVisibilityOff()
    prop.SetPointSize(base_size); prop.SetInterpolationToFlat()
    actor.VisibilityOff() if _opacity <= 0.0 else actor.VisibilityOn()
    p._prev_mode = 'pt_fog'

def build_pt_fog_lut(
    p, cmap_name: str, fog_start: float = POINT_FOG_START,
) -> np.ndarray:
    bg = tuple(p.renderer.GetBackground())
    key = (cmap_name, bg, fog_start)
    if getattr(p, '_pt_fog_lut_key', None) == key:
        return p._pt_fog_lut_cache
    t_vals = np.linspace(0, 1, 256, dtype=np.float32)
    colors = _cm.get_cmap(cmap_name)(t_vals)[:, :3].astype(np.float32)
    bg_arr = np.array(bg, dtype=np.float32)
    depth_dist = 1.0 - t_vals
    _tail = max(1.0 - fog_start, 1e-6)
    fog_t = np.clip(
        (depth_dist - fog_start) / _tail, 0.0, 1.0,
    )[:, np.newaxis]
    lut = ((colors * (1.0 - fog_t) + bg_arr * fog_t) * 255).astype(np.uint8)
    p._pt_fog_lut_cache = lut
    p._pt_fog_lut_key = key
    return lut

def pt_cam_key(p, mesh) -> tuple:
    cam = p.renderer.GetActiveCamera()
    d = cam.GetDirectionOfProjection(); pos = cam.GetPosition()
    return (id(mesh), round(d[0], 5), round(d[1], 5), round(d[2], 5), round(pos[0], 4), round(pos[1], 4), round(pos[2], 4), tuple(p.renderer.GetBackground()))

def apply_pt_normal(p, mesh) -> None:
    _is_np = getattr(p, '_is_np_data', False)
    _sz_def = NP_CLOUD_SIZE_DEFAULT if _is_np else PT_CLOUD_SIZE_DEFAULT
    _pts_color = NP_POINTS_COLOR if _is_np else POINTS_COLOR
    _sh_scale = NP_CLOUD_SHADER_SCALE if _is_np else PT_CLOUD_SHADER_SCALE
    _sh_smin = NP_CLOUD_SHADER_SIZE_MIN if _is_np else PT_CLOUD_SHADER_SIZE_MIN
    _sh_smax = NP_CLOUD_SHADER_SIZE_MAX if _is_np else PT_CLOUD_SHADER_SIZE_MAX

    _base = getattr(p, '_pt_cloud_size', _sz_def)
    use_rgb = getattr(p, '_pt_cloud_use_rgb', True)
    mapper = p._mesh_mapper; actor = p._mesh_actor
    _shader_size = getattr(p, '_pt_shader_size', -1)
    if _shader_size != _base and _shader_size != 0:
        ok = inject_pt_size_shader(
            actor, _base,
            shader_scale=_sh_scale,
            size_min=_sh_smin,
            size_max=_sh_smax,
        )
        p._pt_shader_size = _base if ok else 0
    if _shader_size != 0: update_pt_size_uniforms(p, actor)
    _opacity = getattr(p, '_mesh_opacity', 1.0)
    _color_key = (id(mesh), use_rgb)
    if getattr(p, '_pt_normal_color_key', None) == _color_key:
        actor.GetProperty().SetOpacity(_opacity)
        actor.VisibilityOff() if _opacity <= 0.0 else actor.VisibilityOn()
        return
    p._pt_normal_color_key = _color_key
    cached = _set_mesh_input(mapper, mesh, p, '_cached_mesh_poly')
    if MESH_MATTE_COLOR is not None:
        c = [int(v * 255) for v in _hex_to_rgb(MESH_MATTE_COLOR)]
        raw = np.full((mesh.n_points, 3), c, dtype=np.uint8)
    else:
        raw = _pack_vertex_colors(mesh) if use_rgb else None
        if raw is None:
            c = [int(v * 255) for v in _hex_to_rgb(_pts_color)]
            raw = np.full((mesh.n_points, 3), c, dtype=np.uint8)
    p._pt_color_buf = raw
    vtk_c = numpy_to_vtk(raw, deep=False, array_type=_vtk.VTK_UNSIGNED_CHAR)
    vtk_c.SetName('PtNormalColors')
    cached.GetPointData().SetScalars(vtk_c)
    cached.GetPointData().Modified()
    mapper.ScalarVisibilityOn(); mapper.SetColorModeToDirectScalars()
    actor.SetTexture(None)
    prop = actor.GetProperty()
    prop.SetOpacity(_opacity); prop.SetLighting(False)
    prop.SetRepresentationToSurface(); prop.EdgeVisibilityOff()
    prop.SetPointSize(_base); prop.SetInterpolationToFlat()
    actor.VisibilityOff() if _opacity <= 0.0 else actor.VisibilityOn()
    p._prev_mode = 'pt_normal'

def apply_pt_depth(p, mesh) -> None:
    from process.mode.depth import _compute_depth
    _is_np = getattr(p, '_is_np_data', False)
    _sz_def = NP_CLOUD_SIZE_DEFAULT if _is_np else PT_CLOUD_SIZE_DEFAULT
    _depth_color = NP_CLOUD_DEPTH_COLOR if _is_np else PT_CLOUD_DEPTH_COLOR
    _depth_contrast = NP_CLOUD_DEPTH_CONTRAST if _is_np else PT_CLOUD_DEPTH_CONTRAST
    _fog_start = NP_POINT_FOG_START if _is_np else POINT_FOG_START
    _sh_scale = NP_CLOUD_SHADER_SCALE if _is_np else PT_CLOUD_SHADER_SCALE
    _sh_smin = NP_CLOUD_SHADER_SIZE_MIN if _is_np else PT_CLOUD_SHADER_SIZE_MIN
    _sh_smax = NP_CLOUD_SHADER_SIZE_MAX if _is_np else PT_CLOUD_SHADER_SIZE_MAX

    _base = getattr(p, '_pt_cloud_size', _sz_def)
    _shader_size = getattr(p, '_pt_shader_size', -1)
    if _shader_size != _base and _shader_size != 0:
        ok = inject_pt_size_shader(
            p._mesh_actor, _base,
            shader_scale=_sh_scale,
            size_min=_sh_smin,
            size_max=_sh_smax,
        )
        p._pt_shader_size = _base if ok else 0
    if _shader_size != 0: update_pt_size_uniforms(p, p._mesh_actor)
    _opacity = getattr(p, '_mesh_opacity', 1.0)
    _key = pt_cam_key(p, mesh)
    if getattr(p, '_pt_depth_cache_key', None) == _key:
        p._mesh_actor.GetProperty().SetOpacity(_opacity)
        p._mesh_actor.VisibilityOff() if _opacity <= 0.0 else p._mesh_actor.VisibilityOn()
        return
    p._pt_depth_cache_key = _key
    mapper = p._mesh_mapper; actor = p._mesh_actor
    lut = getattr(p, '_pt_depth_lut', None)
    if lut is None:
        from process.mode.surface import apply_normal
        apply_normal(p, mesh, None); return
    saved_axis = getattr(p, '_depth_axis', 3)
    p._depth_axis = 3; depth = _compute_depth(p, mesh); p._depth_axis = saved_axis
    d_min, d_max = float(depth.min()), float(depth.max()); span = d_max - d_min
    depth_n = (
        np.clip(
            0.5 + ((depth - d_min) / span - 0.5) * _depth_contrast,
            0.0, 1.0,
        ).astype(np.float32)
        if span > 1e-12
        else np.zeros_like(depth, dtype=np.float32)
    )
    fog_lut = build_pt_fog_lut(p, _depth_color, fog_start=_fog_start)
    idx = (depth_n * 255.0).clip(0, 255).astype(np.uint8); blended = fog_lut[idx]
    cached = _set_mesh_input(mapper, mesh, p, '_cached_mesh_poly'); p._pt_color_buf = blended
    vtk_c = numpy_to_vtk(blended, deep=False, array_type=_vtk.VTK_UNSIGNED_CHAR)
    vtk_c.SetName('PtDepthColors'); cached.GetPointData().SetScalars(vtk_c); cached.GetPointData().Modified()
    mapper.ScalarVisibilityOn(); mapper.SetColorModeToDirectScalars(); p._cmap_lut = lut; p._cmap_range = (0.0, 1.0); p._cmap_title = f'DEPTH.{AXIS_NAMES[3]}'
    actor.SetTexture(None); prop = actor.GetProperty()
    prop.SetOpacity(_opacity); prop.SetLighting(False); prop.SetRepresentationToSurface(); prop.EdgeVisibilityOff(); prop.SetPointSize(getattr(p, '_pt_cloud_size', 1)); prop.SetInterpolationToFlat()
    actor.VisibilityOff() if _opacity <= 0.0 else actor.VisibilityOn()
    p._prev_mode = 'pt_depth'

def apply_pt_fog(p, mesh) -> None:
    from process.mode.depth import _compute_depth
    _is_np = getattr(p, '_is_np_data', False)
    _sz_def = NP_CLOUD_SIZE_DEFAULT if _is_np else PT_CLOUD_SIZE_DEFAULT
    _depth_color = NP_CLOUD_DEPTH_COLOR if _is_np else PT_CLOUD_DEPTH_COLOR
    _depth_contrast = NP_CLOUD_DEPTH_CONTRAST if _is_np else PT_CLOUD_DEPTH_CONTRAST
    _fog_start = NP_POINT_FOG_START if _is_np else POINT_FOG_START
    _pts_color = NP_POINTS_COLOR if _is_np else POINTS_COLOR
    _sh_scale = NP_CLOUD_SHADER_SCALE if _is_np else PT_CLOUD_SHADER_SCALE
    _sh_smin = NP_CLOUD_SHADER_SIZE_MIN if _is_np else PT_CLOUD_SHADER_SIZE_MIN
    _sh_smax = NP_CLOUD_SHADER_SIZE_MAX if _is_np else PT_CLOUD_SHADER_SIZE_MAX

    _opacity = getattr(p, '_mesh_opacity', 1.0)
    _base = getattr(p, '_pt_cloud_size', _sz_def)
    use_rgb = getattr(p, '_pt_cloud_use_rgb', False)
    use_depth_cmap = getattr(p, '_pt_cloud_depth', False)
    mapper = p._mesh_mapper; actor = p._mesh_actor
    if not use_depth_cmap:
        _fog_gpu = getattr(p, '_pt_fog_gpu', None)
        _fog_gpu_base = getattr(p, '_pt_fog_gpu_base', -1)
        if _fog_gpu is None or _fog_gpu_base != _base:
            ok = inject_pt_fog_shader(
                actor, _base,
                shader_scale=_sh_scale,
                size_min=_sh_smin,
                size_max=_sh_smax,
                depth_contrast=_depth_contrast,
                fog_start=_fog_start,
            )
            p._pt_fog_gpu = ok; p._pt_fog_gpu_base = _base; _fog_gpu = ok
        if _fog_gpu:
            update_pt_size_uniforms(p, actor)
            _apply_pt_fog_gpu(p, mesh, mapper, actor, _base, use_rgb)
            return
    _shader_size = getattr(p, '_pt_shader_size', -1)
    if _shader_size != _base and _shader_size != 0:
        ok = inject_pt_size_shader(
            actor, _base,
            shader_scale=_sh_scale,
            size_min=_sh_smin,
            size_max=_sh_smax,
        )
        p._pt_shader_size = _base if ok else 0
    if _shader_size != 0: update_pt_size_uniforms(p, actor)
    _key = (pt_cam_key(p, mesh), use_rgb, use_depth_cmap)
    if getattr(p, '_pt_fog_cache_key', None) == _key:
        actor.GetProperty().SetOpacity(_opacity)
        actor.VisibilityOff() if _opacity <= 0.0 else actor.VisibilityOn()
        return
    p._pt_fog_cache_key = _key
    saved_axis = getattr(p, '_depth_axis', 3)
    p._depth_axis = 3; depth = _compute_depth(p, mesh); p._depth_axis = saved_axis
    span = float(depth.max() - depth.min())
    depth_n = (
        np.clip(
            0.5 + ((depth - depth.min()) / span - 0.5) * _depth_contrast,
            0.0, 1.0,
        )
        if span > 1e-12
        else np.zeros(mesh.n_points, dtype=np.float32)
    )
    bg_arr = np.array(p.renderer.GetBackground(), dtype=np.float32)
    if use_depth_cmap:
        fog_lut = build_pt_fog_lut(p, _depth_color, fog_start=_fog_start)
        idx = (depth_n * 255.0).clip(0, 255).astype(np.uint8)
        blended = fog_lut[idx]
    else:
        base_u8 = _pack_vertex_colors(mesh) if use_rgb else None
        if base_u8 is not None:
            base = base_u8.astype(np.float32) / 255.0
        else:
            c = np.array(_hex_to_rgb(_pts_color), dtype=np.float32)
            base = np.full((mesh.n_points, 3), c, dtype=np.float32)
        depth_dist = 1.0 - depth_n
        _tail = max(1.0 - _fog_start, 1e-6)
        t = np.clip(
            (depth_dist - _fog_start) / _tail, 0.0, 1.0,
        )[:, np.newaxis]
        blended = (
            (base * (1.0 - t) + bg_arr * t).clip(0.0, 1.0) * 255
        ).astype(np.uint8)
    cached = _set_mesh_input(mapper, mesh, p, '_cached_mesh_poly'); p._pt_color_buf = blended
    vtk_c = numpy_to_vtk(blended, deep=False, array_type=_vtk.VTK_UNSIGNED_CHAR)
    vtk_c.SetName('PtFogColors'); cached.GetPointData().SetScalars(vtk_c); cached.GetPointData().Modified()
    mapper.ScalarVisibilityOn(); mapper.SetColorModeToDirectScalars()
    actor.SetTexture(None); prop = actor.GetProperty()
    prop.SetOpacity(_opacity); prop.SetLighting(False); prop.SetRepresentationToSurface(); prop.EdgeVisibilityOff(); prop.SetPointSize(getattr(p, '_pt_cloud_size', 1)); prop.SetInterpolationToFlat()
    actor.VisibilityOff() if _opacity <= 0.0 else actor.VisibilityOn()
    p._prev_mode = 'pt_fog'
