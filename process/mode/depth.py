import logging
import numpy as np
import vtk as _vtk
import matplotlib.cm as _cm
from vtk.util.numpy_support import numpy_to_vtk

from configs.settings import (
    DEPTH_SHADING_FLAT, DEPTH_ENABLE_LIGHTING, COLOR_DEPTH,
    POINT_FOG, POINT_FOG_START, PT_CLOUD_DEPTH_CONTRAST,
    PT_CLOUD_SHADER_SCALE, PT_CLOUD_SHADER_SIZE_MIN, PT_CLOUD_SHADER_SIZE_MAX,
    PT_CLOUD_SIZE_DEFAULT,
)
from process.mode.common import _hex_to_rgb, _set_mesh_input
from process.mode.labels import AXIS_NAMES

logger = logging.getLogger(__name__)

_LUT_DEPTH: 'np.ndarray | None' = (
    None if COLOR_DEPTH.startswith('#')
    else (
        _cm.get_cmap(COLOR_DEPTH)(np.linspace(0, 1, 256))[:, :3] * 255
    ).astype(np.uint8)
)

def _compute_bbox_depth_range(p, mesh) -> tuple:
    b = mesh.bounds
    corners = np.array(
        [[x, y, z]
         for x in (b[0], b[1])
         for y in (b[2], b[3])
         for z in (b[4], b[5])],
        dtype=np.float32,
    )
    s = getattr(p, '_norm_scale', 1.0)
    c = np.array(
        getattr(p, '_norm_center', [0.0, 0.0, 0.0]), dtype=np.float32,
    )
    world = s * corners + (1.0 - s) * c
    cam = p.renderer.GetActiveCamera()
    cam_dir = np.array(cam.GetDirectionOfProjection(), dtype=np.float32)
    cam_dir /= np.linalg.norm(cam_dir) + 1e-12
    cam_pos = np.array(cam.GetPosition(), dtype=np.float32)
    depths = -np.dot(world - cam_pos, cam_dir)
    return float(depths.min()), float(depths.max())

def _build_depth_frag_code(fog: bool = True) -> str:
    if COLOR_DEPTH.startswith('#'):
        r, g, b = _hex_to_rgb(COLOR_DEPTH)
        lut_body = ', '.join(
            f'vec3({r:.4f},{g:.4f},{b:.4f})' for _ in range(256)
        )
    else:
        t_vals = np.linspace(0, 1, 256, dtype=np.float32)
        cols = _cm.get_cmap(COLOR_DEPTH)(t_vals)[:, :3]
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
            f'  float _dc = clamp(0.5 + (_dn - 0.5)'
            f' * {PT_CLOUD_DEPTH_CONTRAST:.4f}, 0.0, 1.0);\n'
            '  _color = _color * _dc;\n'
            '  float _dist = 1.0 - _dc;\n'
            f'  float _tail = max(1.0 - {POINT_FOG_START:.4f}, 0.00001);\n'
            f'  float _fog_t = clamp((_dist - {POINT_FOG_START:.4f})'
            f' / _tail, 0.0, 1.0);\n'
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
    actor, is_pc: bool = False, base_size: float = 1.0, fog: bool = True,
) -> bool:
    code = _build_depth_frag_code(fog=fog)
    try:
        sp = actor.GetShaderProperty()
        try:
            sp.ClearAllVertexShaderReplacements()
        except AttributeError:
            pass
        if is_pc:
            scale = PT_CLOUD_SHADER_SCALE * base_size
            size_max = PT_CLOUD_SHADER_SIZE_MAX * base_size
            vert_impl = (
                '  float _ptDist = max(gl_Position.w, 0.001);\n'
                f'  gl_PointSize = clamp({scale:.2f} / _ptDist,'
                f' {PT_CLOUD_SHADER_SIZE_MIN:.2f}, {size_max:.2f});\n'
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
    bg = tuple(p.renderer.GetBackground()) if POINT_FOG else ()
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

def _build_depth_fog_lut(p) -> np.ndarray:
    bg = tuple(p.renderer.GetBackground())
    key = ('depth', bg)
    if getattr(p, '_depth_fog_lut_key', None) == key:
        return p._depth_fog_lut_cache
    t_vals = np.linspace(0, 1, 256, dtype=np.float32)
    if COLOR_DEPTH.startswith('#'):
        base_c = np.array(_hex_to_rgb(COLOR_DEPTH), dtype=np.float32)
        colors = np.tile(base_c, (256, 1))
    else:
        colors = _cm.get_cmap(COLOR_DEPTH)(t_vals)[:, :3].astype(np.float32)
    bg_arr = np.array(bg, dtype=np.float32)
    dc = np.clip(
        0.5 + (t_vals - 0.5) * PT_CLOUD_DEPTH_CONTRAST, 0.0, 1.0,
    )
    colors_mult = colors * dc[:, np.newaxis]
    depth_dist = 1.0 - dc
    _tail = max(1.0 - POINT_FOG_START, 1e-6)
    fog_t = np.clip(
        (depth_dist - POINT_FOG_START) / _tail, 0.0, 1.0,
    )[:, np.newaxis]
    lut = (
        (colors_mult * (1.0 - fog_t) + bg_arr * fog_t) * 255
    ).astype(np.uint8)
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
    lut = getattr(p, '_depth_lut', None)
    axis = getattr(p, '_depth_axis', 3)
    is_pc = (mesh.n_faces_strict == 0)

    _fog_active = (
        is_pc and POINT_FOG and getattr(p, '_pt_fog_enabled', True)
    )

    if axis == 3:
        _base = (
            getattr(p, '_pt_cloud_size', PT_CLOUD_SIZE_DEFAULT)
            if is_pc else None
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
                actor, is_pc=is_pc, base_size=_base or 1.0, fog=_fog_active,
            )
            p._depth_fog_gpu = ok
            p._depth_fog_gpu_base = _base
            p._depth_fog_gpu_fog = _fog_active
            _fog_gpu = ok

        if _fog_gpu:
            d_min, d_max = _compute_bbox_depth_range(p, mesh)
            bg = (
                tuple(p.renderer.GetBackground())
                if _fog_active else (0.0, 0.0, 0.0)
            )
            cam = p.renderer.GetActiveCamera()
            near, far = cam.GetClippingRange()
            _unif_key = (
                round(d_min, 1), round(d_max, 1),
                bg if _fog_active else (),
                round(near, 3), round(far, 1),
                _fog_active,
            )
            if getattr(p, '_depth_unif_key', None) != _unif_key:
                try:
                    _update_depth_uniforms(
                        actor.GetShaderProperty(),
                        d_min, d_max, bg, near, far, fog=_fog_active,
                    )
                    p._depth_unif_key = _unif_key
                except Exception as e:
                    logger.warning('depth uniform update failed: %s', e)
                    p._depth_fog_gpu = False
                    _fog_gpu = False

        if _fog_gpu:
            cached = _set_mesh_input(
                mapper, mesh, p, '_cached_mesh_poly',
            )
            if getattr(p, '_depth_scalar_key', None) != id(mesh):
                cached.GetPointData().SetScalars(None)
                cached.GetPointData().Modified()
                p._depth_scalar_key = id(mesh)
            mapper.ScalarVisibilityOff()
            actor.SetTexture(None)
            prop = actor.GetProperty()
            prop.SetOpacity(1.0)
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
            p._cmap_lut = lut
            p._cmap_range = (d_min, d_max)
            p._cmap_title = f'DEPTH.{AXIS_NAMES[axis]}'
            p._prev_mode = 'depth'
            return

    _key = _depth_cam_key(p, mesh)
    _needs_update = (getattr(p, '_depth_scalar_key', None) != _key)

    if _needs_update:
        p._depth_scalar_key = _key
        depth = _compute_depth(p, mesh)
        d_min, d_max = float(depth.min()), float(depth.max())
        p._depth_d_range = (d_min, d_max)
        span = d_max - d_min
        if span > 1e-12:
            depth_n = ((depth - d_min) / span).astype(np.float32)
        else:
            depth_n = np.zeros_like(depth, dtype=np.float32)

        cached = _set_mesh_input(mapper, mesh, p, '_cached_mesh_poly')

        if _fog_active:
            fog_lut = _build_depth_fog_lut(p)
            idx = (depth_n * 255.0).clip(0, 255).astype(np.uint8)
            blended = fog_lut[idx]
            p._depth_color_buf = blended
            vtk_c = numpy_to_vtk(
                blended, deep=False, array_type=_vtk.VTK_UNSIGNED_CHAR,
            )
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
            if lut is not None:
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

    actor.SetTexture(None)
    prop = actor.GetProperty()
    prop.SetOpacity(1.0)
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

    actor.VisibilityOn()
    p._prev_mode = 'depth'
