import time
import logging
from time import time as _now

import numpy as np
import pyvista as pv

from configs.settings import (
    FNORMAL_MESH_OPACITY,
    STARTUP_MODE_POINT_CLOUD,
    PT_CLOUD_SIZE_DEFAULT,
    PT_CLOUD_SIZE_POINT_WHITE,
    PT_CLOUD_SIZE_DEPTH,
    POINT_FOG,
    MESH_MATTE_COLOR,
    NP_STARTUP_MODE_POINT_CLOUD,
    NP_CLOUD_SIZE_DEFAULT,
    NP_CLOUD_SIZE_POINT_WHITE,
    NP_CLOUD_SIZE_DEPTH,
    NP_POINT_FOG,
)
from process.mode.surface import apply_normal
from process.mode.default import apply_default_reset
from process.mode.isoline import (
    apply_isoline, apply_iso_occluder, apply_iso_only,
)
from process.mode.wire import apply_wire, apply_wire_occluder
from process.mode.edge import apply_edge, apply_edge_occluder
from process.mode.depth import apply_depth
from process.mode.normal_color import apply_normal_color
from process.mode.mesh_quality import apply_mesh_quality
from process.mode.face_normal import apply_face_normal
from process.mode.vtx import apply_vtx_labels
from process.mode.pt_cloud import (
    apply_pt_fog, apply_pt_depth, apply_pt_normal, set_pc_render_quality,
    update_pt_size_uniforms,
)

logger = logging.getLogger(__name__)

_AXIS_SWAP_ORDER = [
    None,
    (0, 2, 1),
    (2, 1, 0),
    (1, 0, 2),
]

def _apply_axis_transform(mesh, swap_idx, reverse):
    pts = mesh.points.copy()
    rx, ry, rz = reverse
    if rx:
        pts[:, 0] *= -1
    if ry:
        pts[:, 1] *= -1
    if rz:
        pts[:, 2] *= -1
    if swap_idx:
        pts = pts[:, list(_AXIS_SWAP_ORDER[swap_idx])]
    result = mesh.copy(deep=True)
    result.points = pts
    return result

_FACE_REQUIRED = {
    '_is_isoline':      'ISOLINE',
    '_is_iso_only':     'ISO.ONLY',
    '_is_mesh_quality': 'MESH.QUALITY',
    '_is_fnormal':      'FACE.NORM',
    '_is_wire':         'WIREFRAME',
    '_is_edge':         'EDGE.EXTRACT',
    '_is_normal_color': 'SURF.NORMAL',
    '_is_smooth':       'SMOOTH',
    '_is_vtx':          'VERTEX.LABEL',
    '_is_lighting':     'MESH.REDUCTION',
}

def apply_point_cloud_startup(p) -> None:
    for attr in _FACE_REQUIRED:
        setattr(p, attr, False)
    p._smooth_cycle = 0
    p._pbr_with_tex = False
    p._is_tex = False

    _is_np = getattr(p, '_is_np_data', False)
    if _is_np:
        mode       = NP_STARTUP_MODE_POINT_CLOUD
        _sz_rgb    = NP_CLOUD_SIZE_DEFAULT
        _sz_white  = NP_CLOUD_SIZE_POINT_WHITE
        _sz_depth  = NP_CLOUD_SIZE_DEPTH
        p._pt_fog_enabled = NP_POINT_FOG
    else:
        mode       = STARTUP_MODE_POINT_CLOUD
        _sz_rgb    = PT_CLOUD_SIZE_DEFAULT
        _sz_white  = PT_CLOUD_SIZE_POINT_WHITE
        _sz_depth  = PT_CLOUD_SIZE_DEPTH
        p._pt_fog_enabled = POINT_FOG

    if mode == 'point_rgb':
        p._pt_cloud_use_rgb = True
        p._pt_cloud_depth = False
        p._pt_cloud_size = _sz_rgb
    elif mode == 'point_white':
        p._pt_cloud_use_rgb = False
        p._pt_cloud_depth = False
        p._pt_cloud_size = _sz_white
        p._pt_cloud_color = 'red'
    elif mode == 'depth':
        p._is_depth = True
        p._pt_cloud_size = _sz_depth
    else:
        p._pt_cloud_use_rgb = True
        p._pt_cloud_depth = False
        p._pt_cloud_size = _sz_rgb
    logger.info(
        'Point cloud startup mode: %s%s',
        mode, ' [NP]' if _is_np else '',
    )

_apply_point_cloud_startup = apply_point_cloud_startup

def _active_face_mode(p) -> str | None:
    for attr, name in _FACE_REQUIRED.items():
        if getattr(p, attr, False):
            return name
    return None

def _active_mode_name(p) -> str:
    return _active_face_mode(p) or 'UNKNOWN'

def sync_pt_size_uniforms(p) -> None:
    if getattr(p, '_n_faces', 1) == 0:
        if hasattr(p, '_mesh_actor'):
            update_pt_size_uniforms(p, p._mesh_actor)

def apply_visual_mode(plotter, mesh, preloaded_tex):
    p = plotter
    t_total = time.perf_counter()

    reduction = getattr(p, '_reduction_mesh', 1.0)
    if reduction < 1.0:
        if mesh.n_faces_strict == 0:
            n_pts = mesh.n_points
            target = max(1, int(n_pts * reduction))
            step = max(1, n_pts // target)
            indices = np.arange(0, n_pts, step)
            sub = pv.PolyData(mesh.points[indices])
            for key in mesh.point_data.keys():
                arr = mesh.point_data[key]
                if len(arr) == n_pts:
                    sub.point_data[key] = arr[indices]
            mesh = sub
            p._cached_mesh_poly = None
            p._cached_wire_poly_src = None
            p._cached_edge_poly_src = None
            p._cached_iso_display_src = None
            p._cached_fnormal_src = None
            p._cached_vtx_src = None
            logger.debug(
                'Point cloud manual subsampled: %d -> %d pts'
                ' (reduction=%.2f)',
                n_pts, mesh.n_points, reduction,
            )
        else:
            if not mesh.is_all_triangles:
                mesh = mesh.triangulate()
            mesh = mesh.decimate(1.0 - reduction)
            p._cached_mesh_poly = None
            p._cached_wire_poly = None
            p._cached_wire_poly_src = None
            p._cached_edge_poly_src = None
            p._cached_iso_display_src = None
            p._cached_fnormal_src = None
            p._cached_vtx_src = None
    swap = getattr(p, '_axis_swap', 0)
    reverse = getattr(p, '_axis_reverse', (False, False, False))
    if swap != 0 or any(reverse):
        cache_key = (id(mesh), swap, reverse)
        if getattr(p, '_axis_swap_cache_key', None) == cache_key:
            mesh = p._axis_swap_cached_mesh
        else:
            mesh = _apply_axis_transform(mesh, swap, reverse)
            p._axis_swap_cache_key = cache_key
            p._axis_swap_cached_mesh = mesh

    p._n_points = mesh.n_points
    p._n_faces = mesh.n_faces_strict
    p._cmap_lut = None
    p._last_preloaded_tex = preloaded_tex

    if not getattr(p, '_pt_cloud_startup_done', False):
        p._pt_cloud_startup_done = True
        if p._n_faces == 0:
            apply_default_reset(p)
            _apply_point_cloud_startup(p)
            set_pc_render_quality(p, True)

    sync_pt_size_uniforms(p)

    if mesh.n_faces_strict == 0:
        mode_name = _active_face_mode(p)
        if mode_name is not None:
            msg = (
                f'[Error] Not supported "{mode_name}"'
                f' for point clouds.'
                f' (no faces). Reverting to default.'
            )
            logger.error(msg)
            p._render_error = msg
            p._error_msg = msg
            p._error_msg_time = _now()
            apply_default_reset(p)
            apply_normal(p, mesh, preloaded_tex)
            return

    if p._is_isoline:
        t0 = time.perf_counter()
        apply_isoline(p, mesh)
        apply_iso_occluder(p, mesh)
        p._isoline_visible = True
        logger.debug(
            'apply_isoline: %.4fs', time.perf_counter() - t0
        )
    elif getattr(p, '_isoline_visible', False):
        p._iso_actor.VisibilityOff()
        p._isoline_visible = False
        p._mesh_actor.VisibilityOn()

    if p._is_wire:
        t0 = time.perf_counter()
        apply_wire(p, mesh)
        apply_wire_occluder(p, mesh)
        p._wire_visible = True
        logger.debug(
            'apply_wire: %.4fs', time.perf_counter() - t0
        )
    elif getattr(p, '_wire_visible', False):
        p._wire_actor.VisibilityOff()
        p._wire_visible = False
        p._mesh_actor.VisibilityOn()
        p._prev_mode = None

    if getattr(p, '_is_edge', False):
        t0 = time.perf_counter()
        apply_edge(p, mesh)
        apply_edge_occluder(p, mesh)
        p._edge_visible = True
        logger.debug(
            'apply_edge: %.4fs', time.perf_counter() - t0
        )
    elif getattr(p, '_edge_visible', False):
        p._edge_actor.VisibilityOff()
        p._edge_visible = False
        p._mesh_actor.VisibilityOn()
        p._prev_mode = None

    if p._is_iso_only:
        t0 = time.perf_counter()
        apply_iso_only(p, mesh)
        logger.debug(
            'apply_iso_only: %.4fs', time.perf_counter() - t0
        )
    elif (not p._is_isoline and not p._is_wire
            and not getattr(p, '_is_edge', False)
            and not getattr(p, '_is_fnormal', False)):
        t0 = time.perf_counter()
        if MESH_MATTE_COLOR is not None:
            _prev = getattr(p, '_prev_mode', None)
            if not isinstance(_prev, tuple):
                try:
                    sp = p._mesh_actor.GetShaderProperty()
                    sp.ClearAllVertexShaderReplacements()
                    sp.SetFragmentShaderCode('')
                except AttributeError:
                    pass
                p._prev_mode = None
                p._depth_fog_gpu = None
                p._pt_shader_size = -1
            if p._n_faces == 0:
                apply_pt_normal(p, mesh)
                logger.debug(
                    'apply_matte_pt: %.4fs', time.perf_counter() - t0,
                )
            else:
                apply_normal(p, mesh, preloaded_tex)
                logger.debug(
                    'apply_matte_mesh: %.4fs', time.perf_counter() - t0,
                )
        elif getattr(p, '_is_normal_color', False):
            apply_normal_color(p, mesh)
            logger.debug(
                'apply_normal_color: %.4fs',
                time.perf_counter() - t0,
            )
        elif getattr(p, '_is_mesh_quality', False):
            apply_mesh_quality(p, mesh)
            logger.debug(
                'apply_mesh_quality: %.4fs',
                time.perf_counter() - t0,
            )
        elif getattr(p, '_is_depth', False):
            apply_depth(p, mesh)
            logger.debug(
                'apply_depth: %.4fs', time.perf_counter() - t0,
            )
        elif (p._n_faces == 0
                and getattr(p, '_pt_fog_enabled', False)):
            apply_pt_fog(p, mesh)
            logger.debug(
                'apply_pt_fog: %.4fs', time.perf_counter() - t0,
            )
        elif p._n_faces == 0:
            apply_pt_normal(p, mesh)
            logger.debug(
                'apply_pt_normal: %.4fs', time.perf_counter() - t0,
            )
        else:
            apply_normal(p, mesh, preloaded_tex)
            logger.debug(
                'apply_normal: %.4fs', time.perf_counter() - t0
            )

    if getattr(p, '_is_fnormal', False):
        t0 = time.perf_counter()
        apply_face_normal(p, mesh)
        if getattr(p, '_fnormal_mesh_hidden', False):
            p._mesh_actor.VisibilityOff()
        else:
            apply_normal(p, mesh, preloaded_tex)

            target_opacity = FNORMAL_MESH_OPACITY if getattr(p, '_mesh_opacity', 1.0) > 0.0 else 0.0
            p._mesh_actor.GetProperty().SetOpacity(target_opacity)
        logger.debug(
            'apply_face_normal: %.4fs', time.perf_counter() - t0
        )
    elif hasattr(p, '_fnormal_actor'):
        p._fnormal_actor.VisibilityOff()

    if getattr(p, '_is_vtx', False):
        apply_vtx_labels(p, mesh)
        if getattr(p, '_vtx_mesh_hidden', False):
            p._mesh_actor.VisibilityOff()
    elif hasattr(p, '_vtx_label_actor'):
        p._vtx_label_actor.VisibilityOff()
        if hasattr(p, '_vtx_point_actor'):
            p._vtx_point_actor.VisibilityOff()
        if hasattr(p, '_vtx_sel_actor'):
            p._vtx_sel_actor.VisibilityOff()
        if hasattr(p, '_vtx_pick_text'):
            p._vtx_pick_text.VisibilityOff()
        p._vtx_world_pts = None
        p._vtx_indices = None

    logger.debug(
        'apply_visual_mode total: %.4fs',
        time.perf_counter() - t_total,
    )
