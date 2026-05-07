import logging
import platform as _platform
import numpy as np
import vtk as _vtk
import matplotlib.cm as _cm
from vtk.util.numpy_support import numpy_to_vtk

from configs.settings import (
    DEPTH_SHADING_FLAT, DEPTH_ENABLE_LIGHTING,
    MESH_DEPTH_COLOR, PT_CLOUD_DEPTH_COLOR,
    POINT_FOG_START, PT_CLOUD_DEPTH_CONTRAST,
    PT_CLOUD_SHADER_SCALE, PT_CLOUD_SHADER_SIZE_MIN, PT_CLOUD_SHADER_SIZE_MAX,
    PT_CLOUD_SIZE_DEFAULT,
    NP_POINT_FOG_START, NP_CLOUD_DEPTH_CONTRAST,
    NP_CLOUD_DEPTH_COLOR,
    NP_CLOUD_SHADER_SCALE, NP_CLOUD_SHADER_SIZE_MIN, NP_CLOUD_SHADER_SIZE_MAX,
    NP_CLOUD_SIZE_DEFAULT,
)
from process.mode.common import _hex_to_rgb, _set_mesh_input, _make_vtk_lut
from process.mode.labels import AXIS_NAMES

logger = logging.getLogger(__name__)
_IS_WSL2 = 'microsoft' in _platform.uname().release.lower()

_LUT_DEPTH: 'np.ndarray | None' = (
    None if MESH_DEPTH_COLOR.startswith('#')
    else (
        _cm.get_cmap(MESH_DEPTH_COLOR)(np.linspace(0, 1, 256))[:, :3] * 255
    ).astype(np.uint8)
)

def _compute_bbox_depth_range(p, mesh) -> tuple:
    b = mesh.bounds
    corners = np.array(
        [[x, y, z]
         for x in (b[0], b[1])
         for y in (b[2], b[3])
         for z in (b[4], b[5])],
        dtype=np.float64,
    )
    s = float(getattr(p, '_norm_scale', 1.0))
    c = np.array(
        getattr(p, '_norm_center', [0.0, 0.0, 0.0]), dtype=np.float64,
    )
    world = s * corners + (1.0 - s) * c
    cam = p.renderer.GetActiveCamera()
    cam_dir = np.array(cam.GetDirectionOfProjection(), dtype=np.float64)
    cam_dir /= np.linalg.norm(cam_dir) + 1e-12
    cam_pos = np.array(cam.GetPosition(), dtype=np.float64)
    depths = -np.dot(world - cam_pos, cam_dir)
    return float(depths.min()), float(depths.max())

def _build_depth_frag_code(
    fog: bool = True,
    is_pc: bool = False,
    depth_color: 'str | None' = None,
    depth_contrast: float = PT_CLOUD_DEPTH_CONTRAST,
    fog_start: float = POINT_FOG_START,
) -> str:
    _color = (
        depth_color if depth_color is not None
        else (PT_CLOUD_DEPTH_COLOR if is_pc else MESH_DEPTH_COLOR)
    )
    if _color.startswith('#'):
        r, g, b = _hex_to_rgb(_color)
        lut_body = ', '.join(
            f'vec3({r:.4f},{g:.4f},{b:.4f})' for _ in range(256)
        )
    else:
        t_vals = np.linspace(0, 1, 256, dtype=np.float32)
        cols = _cm.get_cmap(_color)(t_vals)[:, :3]
        lut_body = ', '.join(
            f'vec3({c[0]:.4f},{c[1]:.4f},{c[2]:.4f})' for c in cols
        )

    depth_code = (
        '  float _linear = u_near * u_far / max(\n'
        '    u_far - gl_FragCoord.z * (u_far - u_near), 0.001);\n'
        '  float _cpu_d = -_linear;\n'
        '  float _span = max(u_dmax - u_dmin, 0.001);\n'
        '  float _dn = clamp((_cpu_d - u_dmin) / _span, 0.0, 1.0);\n'
        '  int _i = int(clamp(_dn * 255.0, 0.0, 255.0));\n'
        '  vec3 _color = _depth_lut[_i];\n'
    )
    if fog:
        fog_uniforms = (
            'uniform float u_bg_r;\n'
            'uniform float u_bg_g;\n'
            'uniform float u_bg_b;\n'
        )
        fog_code = (
            f'  float _dc = clamp(0.5 + (_dn - 0.5) * {depth_contrast:.4f}, 0.0, 1.0);\n'
            '  _color = _color * _dc;\n'
            '  float _dist = 1.0 - _dc;\n'
            f'  float _tail = max(1.0 - {fog_start:.4f}, 0.00001);\n'
            f'  float _fog_t = clamp((_dist - {fog_start:.4f}) / _tail, 0.0, 1.0);\n'
            '  _color = mix(_color, vec3(u_bg_r, u_bg_g, u_bg_b), _fog_t);\n'
        )
    else:
        fog_uniforms = ''
        fog_code = ''

    return (
        '//VTK::System::Dec\n'
        'out vec4 fragOutput0;\n'
        'uniform float u_dmin;\n'
        'uniform float u_dmax;\n'
        'uniform float u_near;\n'
        'uniform float u_far;\n'
        + fog_uniforms
        + f'const vec3 _depth_lut[256] = vec3[]({lut_body});\n'
        'void main() {\n'
        + depth_code
        + fog_code
        + '  fragOutput0 = vec4(_color, 1.0);\n'
        '}\n'
    )

def inject_depth_gpu_shader(
    actor,
    is_pc: bool = False,
    base_size: float = 1.0,
    fog: bool = True,
    depth_color: 'str | None' = None,
    depth_contrast: float = PT_CLOUD_DEPTH_CONTRAST,
    fog_start: float = POINT_FOG_START,
    shader_scale: float = PT_CLOUD_SHADER_SCALE,
    shader_size_min: float = PT_CLOUD_SHADER_SIZE_MIN,
    shader_size_max: float = PT_CLOUD_SHADER_SIZE_MAX,
) -> bool:
    if _IS_WSL2:
        logger.info(
            'WSL2: GPU depth shader disabled, using CPU path'
        )
        return False
    code = _build_depth_frag_code(
        fog=fog, is_pc=is_pc,
        depth_color=depth_color,
        depth_contrast=depth_contrast,
        fog_start=fog_start,
    )
    try:
        sp = actor.GetShaderProperty()
        try:
            sp.ClearAllVertexShaderReplacements()
        except AttributeError:
            pass
        if is_pc:
            scale = shader_scale * base_size
            size_max = shader_size_max * base_size

            vert_dec = (
                '//VTK::Camera::Dec\n'
                'uniform float u_ptCamDist;\n'
                'uniform float u_ptProjScale;\n'
            )
            vert_impl = (
                '  float _ptDist = max(u_ptCamDist, 0.001);\n'
                f'  gl_PointSize = clamp({scale:.4f} * u_ptProjScale / _ptDist,'
                f' {shader_size_min:.2f}, {size_max:.2f});\n'
            )
            sp.AddVertexShaderReplacement(
                '//VTK::Camera::Dec', False, vert_dec, False,
            )
            sp.AddVertexShaderReplacement(
                '//VTK::PositionVC::Impl', False, vert_impl, False,
            )
        sp.SetFragmentShaderCode(code)
        return True
    except Exception as e:
        logger.warning('depth gpu shader injection failed: %s', e)
        return False

def _update_depth_uniforms(
    sp, d_min: float, d_max: float, bg: tuple,
    near: float, far: float, fog: bool = True,
) -> None:
    vu = sp.GetFragmentCustomUniforms()
    vu.SetUniformf('u_dmin', d_min)
    vu.SetUniformf('u_dmax', d_max)
    vu.SetUniformf('u_near', near)
    vu.SetUniformf('u_far', far)
    if fog:
        vu.SetUniformf('u_bg_r', bg[0])
        vu.SetUniformf('u_bg_g', bg[1])
        vu.SetUniformf('u_bg_b', bg[2])

def _depth_cam_key(p, mesh) -> tuple:
    axis = getattr(p, '_depth_axis', 3)
    _fog_flag = getattr(p, '_pt_fog_enabled', False)
    bg = tuple(p.renderer.GetBackground()) if _fog_flag else ()
    if axis != 3:
        return (id(mesh), axis, bg)
    cam = p.renderer.GetActiveCamera()
    d = cam.GetDirectionOfProjection()
    pos = cam.GetPosition()
    return (
        id(mesh),
        round(d[0], 5), round(d[1], 5), round(d[2], 5),
        round(pos[0], 4), round(pos[1], 4), round(pos[2], 4),
        bg,
    )

def _build_depth_fog_lut(p, is_pc: bool = False) -> np.ndarray:
    _is_np = getattr(p, '_is_np_data', False)
    bg = tuple(p.renderer.GetBackground())
    key = ('depth', bg, is_pc, _is_np)
    if getattr(p, '_depth_fog_lut_key', None) == key:
        return p._depth_fog_lut_cache
    if is_pc:
        _color = NP_CLOUD_DEPTH_COLOR if _is_np else PT_CLOUD_DEPTH_COLOR
        _contrast = NP_CLOUD_DEPTH_CONTRAST if _is_np else PT_CLOUD_DEPTH_CONTRAST
        _fog_start = NP_POINT_FOG_START if _is_np else POINT_FOG_START
    else:
        _color = MESH_DEPTH_COLOR
        _contrast = PT_CLOUD_DEPTH_CONTRAST
        _fog_start = POINT_FOG_START
    t_vals = np.linspace(0, 1, 256, dtype=np.float32)
    if _color.startswith('#'):
        base_c = np.array(_hex_to_rgb(_color), dtype=np.float32)
        colors = np.tile(base_c, (256, 1))
    else:
        colors = _cm.get_cmap(_color)(t_vals)[:, :3].astype(np.float32)
    bg_arr = np.array(bg, dtype=np.float32)
    dc = np.clip(0.5 + (t_vals - 0.5) * _contrast, 0.0, 1.0)
    colors_mult = colors * dc[:, np.newaxis]
    depth_dist = 1.0 - dc
    _tail = max(1.0 - _fog_start, 1e-6)
    fog_t = np.clip(
        (depth_dist - _fog_start) / _tail, 0.0, 1.0,
    )[:, np.newaxis]
    lut = ((colors_mult * (1.0 - fog_t) + bg_arr * fog_t) * 255).astype(np.uint8)
    p._depth_fog_lut_cache = lut
    p._depth_fog_lut_key = key
    return lut

def _compute_depth(p, mesh):
    axis = getattr(p, '_depth_axis', 3)
    if axis != 3:
        return mesh.points[:, axis].astype(np.float32)
    s = getattr(p, '_norm_scale', 1.0)
    c = np.array(getattr(p, '_norm_center', [0.0, 0.0, 0.0]))
    world_pts = s * mesh.points + (1.0 - s) * c
    cam = p.renderer.GetActiveCamera()
    cam_dir = np.array(cam.GetDirectionOfProjection())
    cam_dir = cam_dir / (np.linalg.norm(cam_dir) + 1e-12)
    cam_pos = np.array(cam.GetPosition())
    return -np.dot(world_pts - cam_pos, cam_dir).astype(np.float32)

def apply_depth(p, mesh):
    mapper = p._mesh_mapper
    actor = p._mesh_actor
    axis = getattr(p, '_depth_axis', 3)
    is_pc = (mesh.n_faces_strict == 0)

    _is_np = getattr(p, '_is_np_data', False)
    _fog_active = is_pc and getattr(p, '_pt_fog_enabled', False)

    if axis == 3:
        from process.mode.pt_cloud import update_pt_size_uniforms

        _sz_def = NP_CLOUD_SIZE_DEFAULT if _is_np else PT_CLOUD_SIZE_DEFAULT
        _base = (
            getattr(p, '_pt_cloud_size', _sz_def) if is_pc else None
        )
        _fog_gpu = getattr(p, '_depth_fog_gpu', None)
        _fog_gpu_base = getattr(p, '_depth_fog_gpu_base', -1)
        _fog_gpu_fog = getattr(p, '_depth_fog_gpu_fog', None)

        if (
            _fog_gpu is None
            or (is_pc and _fog_gpu_base != _base)
            or _fog_gpu_fog != _fog_active
        ):
            ok = inject_depth_gpu_shader(
                actor,
                is_pc=is_pc,
                base_size=_base or 1.0,
                fog=_fog_active,
                depth_color=(
                    NP_CLOUD_DEPTH_COLOR if _is_np else PT_CLOUD_DEPTH_COLOR
                ) if is_pc else None,
                depth_contrast=(
                    NP_CLOUD_DEPTH_CONTRAST if _is_np
                    else PT_CLOUD_DEPTH_CONTRAST
                ),
                fog_start=(
                    NP_POINT_FOG_START if _is_np else POINT_FOG_START
                ),
                shader_scale=(
                    NP_CLOUD_SHADER_SCALE if _is_np
                    else PT_CLOUD_SHADER_SCALE
                ),
                shader_size_min=(
                    NP_CLOUD_SHADER_SIZE_MIN if _is_np
                    else PT_CLOUD_SHADER_SIZE_MIN
                ),
                shader_size_max=(
                    NP_CLOUD_SHADER_SIZE_MAX if _is_np
                    else PT_CLOUD_SHADER_SIZE_MAX
                ),
            )
            p._depth_fog_gpu = ok
            p._depth_fog_gpu_base = _base
            p._depth_fog_gpu_fog = _fog_active
            _fog_gpu = ok

        if _fog_gpu:
            if is_pc:
                update_pt_size_uniforms(p, actor)

            d_min, d_max = _compute_bbox_depth_range(p, mesh)
            bg = tuple(p.renderer.GetBackground()) if _fog_active else (0.0, 0.0, 0.0)
            cam = p.renderer.GetActiveCamera()
            near, far = cam.GetClippingRange()
            _unif_key = (round(d_min, 1), round(d_max, 1), bg if _fog_active else (), round(near, 3), round(far, 1), _fog_active)
            if getattr(p, '_depth_unif_key', None) != _unif_key:
                try:
                    _update_depth_uniforms(actor.GetShaderProperty(), d_min, d_max, bg, near, far, fog=_fog_active)
                    p._depth_unif_key = _unif_key
                except Exception as e:
                    logger.warning('depth uniform update failed: %s', e)
                    p._depth_fog_gpu = False
                    _fog_gpu = False

        if _fog_gpu:
            cached = _set_mesh_input(mapper, mesh, p, '_cached_mesh_poly')
            if getattr(p, '_depth_scalar_key', None) != id(mesh):
                cached.GetPointData().SetScalars(None)
                cached.GetPointData().Modified()
                p._depth_scalar_key = id(mesh)
            mapper.ScalarVisibilityOff()
            actor.SetTexture(None)
            prop = actor.GetProperty()
            prop.SetOpacity(getattr(p, '_mesh_opacity', 1.0))
            prop.SetLighting(False)
            prop.SetRepresentationToSurface()
            prop.EdgeVisibilityOff()
            _is_smooth_shading = getattr(p, '_is_smooth_shading', False)
            if DEPTH_SHADING_FLAT and not _is_smooth_shading:
                prop.SetInterpolationToFlat()
            else:
                prop.SetInterpolationToPhong()
            is_backface = getattr(p, '_is_backface', True)
            if is_backface:
                prop.BackfaceCullingOn()
            else:
                prop.BackfaceCullingOff()
            if is_pc and _base is not None:
                prop.SetPointSize(_base)
            actor.VisibilityOn()
            p._cmap_lut = None
            p._cmap_range = (d_min, d_max)
            p._cmap_title = f'DEPTH.{AXIS_NAMES[axis]}'
            p._prev_mode = 'depth'
            return

    if getattr(p, '_depth_fog_gpu', None):
        try:
            sp = actor.GetShaderProperty()
            sp.ClearAllVertexShaderReplacements()
            sp.SetFragmentShaderCode('')
        except AttributeError:
            pass
        p._depth_fog_gpu = None
        p._depth_unif_key = None
        p._depth_scalar_key = None

    _color = (
        NP_CLOUD_DEPTH_COLOR if (_is_np and is_pc)
        else (PT_CLOUD_DEPTH_COLOR if is_pc else MESH_DEPTH_COLOR)
    )
    _lut_key = ('depth_cpu', _color)
    if getattr(p, '_depth_lut_cache_key', None) != _lut_key:
        if _color.startswith('#'):
            r, g, b = _hex_to_rgb(_color)
            _lut_obj = _vtk.vtkLookupTable()
            _lut_obj.SetNumberOfColors(256)
            _lut_obj.Build()
            for i in range(256):
                _lut_obj.SetTableValue(i, r, g, b, 1.0)
            p._depth_lut = _lut_obj
        else:
            p._depth_lut = _make_vtk_lut(_color)
        p._depth_lut_cache_key = _lut_key
    lut = p._depth_lut

    _key = _depth_cam_key(p, mesh)
    _needs_update = (getattr(p, '_depth_scalar_key', None) != _key)

    if _needs_update:
        p._depth_scalar_key = _key
        depth = _compute_depth(p, mesh)
        d_min, d_max = float(depth.min()), float(depth.max())
        p._depth_d_range = (d_min, d_max)
        span = d_max - d_min
        depth_n = ((depth - d_min) / span).astype(np.float32) if span > 1e-12 else np.zeros_like(depth, dtype=np.float32)

        cached = _set_mesh_input(mapper, mesh, p, '_cached_mesh_poly')

        if _fog_active:
            fog_lut = _build_depth_fog_lut(p, is_pc=is_pc)
            idx = (depth_n * 255.0).clip(0, 255).astype(np.uint8)
            blended = fog_lut[idx]
            p._depth_color_buf = blended
            vtk_c = numpy_to_vtk(blended, deep=False, array_type=_vtk.VTK_UNSIGNED_CHAR)
            vtk_c.SetName('DepthFogColors')
            cached.GetPointData().SetScalars(vtk_c)
            cached.GetPointData().Modified()
            mapper.ScalarVisibilityOn()
            mapper.SetColorModeToDirectScalars()
        else:
            p._depth_scalar_buf = depth_n.astype(np.float64)
            vtk_d = numpy_to_vtk(p._depth_scalar_buf, deep=False)
            vtk_d.SetName('DepthScalars')
            cached.GetPointData().SetScalars(vtk_d)
            cached.GetPointData().Modified()
            mapper.SetLookupTable(lut)
            mapper.SetScalarRange(0.0, 1.0)
            mapper.ScalarVisibilityOn()
            mapper.SetColorModeToMapScalars()
    else:
        d_min, d_max = getattr(p, '_depth_d_range', (0.0, 1.0))
        _set_mesh_input(mapper, mesh, p, '_cached_mesh_poly')

    p._cmap_lut = lut
    p._cmap_range = (d_min, d_max)
    p._cmap_title = f'DEPTH.{AXIS_NAMES[axis]}'
    _opacity = getattr(p, '_mesh_opacity', 1.0)
    actor.SetTexture(None)
    prop = actor.GetProperty()
    prop.SetOpacity(_opacity)
    prop.SetLighting(DEPTH_ENABLE_LIGHTING)
    prop.SetRepresentationToSurface()
    prop.EdgeVisibilityOff()
    _is_smooth_shading = getattr(p, '_is_smooth_shading', False)
    if DEPTH_SHADING_FLAT and not _is_smooth_shading:
        prop.SetInterpolationToFlat()
    else:
        prop.SetInterpolationToPhong()
    is_backface = getattr(p, '_is_backface', True)
    if is_backface:
        prop.BackfaceCullingOn()
    else:
        prop.BackfaceCullingOff()
    if is_pc:
        _sz_def = NP_CLOUD_SIZE_DEFAULT if _is_np else PT_CLOUD_SIZE_DEFAULT
        prop.SetPointSize(getattr(p, '_pt_cloud_size', _sz_def))
    actor.VisibilityOff() if _opacity <= 0.0 else actor.VisibilityOn()
    p._prev_mode = 'depth'
