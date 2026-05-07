import os
import time

from configs.settings import (
    SHOW_GRID, SHOW_BBOX, SHOW_BACKFACE, SHOW_LIGHTING,
    SHOW_TURNTABLE, SHOW_COLORBAR, SHOW_IMAGE_SEQUENCE,
    SHOW_MESH,
    EDGE_FEATURE_ANGLE,
    ISO_COUNT_DEFAULT, REDUCTION_MESH,
    VTX_SPATIAL_INTERVAL,
    PT_CLOUD_SIZE_DEFAULT, PT_CLOUD_SIZE_POINT_WHITE, PT_CLOUD_SIZE_DEPTH,
    STARTUP_MODE, STARTUP_MODE_POINT_CLOUD,
    POINT_FOG,
    NP_STARTUP_MODE_POINT_CLOUD,
    NP_CLOUD_SIZE_DEFAULT, NP_CLOUD_SIZE_POINT_WHITE, NP_CLOUD_SIZE_DEPTH,
    resolve_axis_settings,
)
from process.mode.labels import (
    SMOOTH_CYCLE_LABELS,
    LBL_PT_CLOUD_RGB, LBL_PT_CLOUD_WHITE, LBL_PT_CLOUD_DEPTH,
)

_AXIS_SWAP_MAP = {'OFF': 0, 'YZ': 1, 'XZ': 2, 'XY': 3}

_STARTUP_FLAG_MAP = {
    'wire':         '_is_wire',
    'smooth':       '_is_smooth_shading',
    'isoline':      '_is_isoline',
    'normal_color': '_is_normal_color',
    'mesh_quality': '_is_mesh_quality',
    'face_normal':  '_is_fnormal',
    'depth':        '_is_depth',
    'edge':         '_is_edge',
    'vtx':          '_is_vtx',
}

_SMOOTH_STARTUP_MAP = {
    'pbr_tex.tex': 0,
    'pbr_tex.pbr': 1,
    'pbr_tex':     2,
}

def restore_startup_mode(p) -> str:
    if getattr(p, '_n_faces', 1) == 0:
        _is_np = getattr(p, '_is_np_data', False)
        mode = NP_STARTUP_MODE_POINT_CLOUD if _is_np else STARTUP_MODE_POINT_CLOUD
        if _is_np:
            _sz_rgb, _sz_white, _sz_depth = (
                NP_CLOUD_SIZE_DEFAULT, NP_CLOUD_SIZE_POINT_WHITE, NP_CLOUD_SIZE_DEPTH
            )
        else:
            _sz_rgb, _sz_white, _sz_depth = (
                PT_CLOUD_SIZE_DEFAULT, PT_CLOUD_SIZE_POINT_WHITE, PT_CLOUD_SIZE_DEPTH
            )
        if mode == 'point_rgb':
            p._pt_cloud_use_rgb = True
            p._pt_cloud_depth = False
            p._pt_cloud_size = _sz_rgb
            return LBL_PT_CLOUD_RGB
        elif mode == 'point_white':
            p._pt_cloud_use_rgb = False
            p._pt_cloud_depth = False
            p._pt_cloud_size = _sz_white
            return LBL_PT_CLOUD_WHITE
        elif mode == 'depth':
            p._is_depth = True
            p._pt_cloud_depth = True
            p._pt_cloud_size = _sz_depth
            return LBL_PT_CLOUD_DEPTH
        return ''
    idx = _SMOOTH_STARTUP_MAP.get(STARTUP_MODE)
    if idx is not None:
        fn = getattr(p, '_apply_smooth_cycle', None)
        if fn:
            p._is_smooth = True
            p._smooth_cycle = idx
            fn(idx)
            return SMOOTH_CYCLE_LABELS[idx]
    else:
        flag = _STARTUP_FLAG_MAP.get(STARTUP_MODE)
        if flag:
            setattr(p, flag, True)
            return STARTUP_MODE.upper()
    return ''

def _apply_startup_mode(plotter) -> None:
    idx = _SMOOTH_STARTUP_MAP.get(STARTUP_MODE)
    if idx is not None:
        plotter._is_smooth = True
        plotter._smooth_cycle = idx
        if idx == 0:
            plotter._is_tex = True
        elif idx == 1:
            plotter._is_lighting = True
        else:
            plotter._is_lighting = True
            plotter._is_tex = True
            plotter._pbr_with_tex = True
    else:
        flag = _STARTUP_FLAG_MAP.get(STARTUP_MODE)
        if flag:
            setattr(plotter, flag, True)

def init_plotter_state(plotter, args) -> None:
    plotter._start_time = time.time()
    plotter._input_name = args.input
    plotter._input_path = getattr(args, 'input_path', args.input)
    plotter._idx = 0
    plotter._save_path = args.save or None
    plotter._save_dir = args.save or None
    plotter._save_loop = args.continuous
    plotter._save_counter = 0
    plotter._is_playing = args.animation
    plotter._is_smooth = args.smooth
    plotter._smooth_cycle = 0
    plotter._pbr_with_tex = False
    plotter._prev_pbr_tex = None
    plotter._hdri_rotation = 0.0
    plotter._is_smooth_shading = False
    plotter._is_wire = False
    plotter._wire_mesh_hidden = True
    plotter._wire_axis = 3
    plotter._wire_visible = False
    plotter._is_tex = args.texture
    plotter._is_grid = SHOW_GRID
    plotter._is_bbox = SHOW_BBOX
    plotter._is_isoline = False
    plotter._isoline_visible = False
    plotter._is_iso_only = False
    plotter._is_lighting = SHOW_LIGHTING
    plotter._is_backface = SHOW_BACKFACE
    plotter._mesh_opacity = 1.0 if SHOW_MESH else 0.0
    plotter._vtx_mesh_hidden = False
    plotter._is_normal_color = False
    plotter._is_mesh_quality = False
    plotter._is_depth = False
    plotter._depth_axis = 3
    plotter._is_vtx = False
    plotter._vtx_spatial_interval = VTX_SPATIAL_INTERVAL
    plotter._is_fnormal = False
    plotter._fnormal_mesh_hidden = True
    plotter._fnormal_axis = 3
    plotter._is_edge = False
    plotter._edge_visible = False
    plotter._edge_mesh_hidden = False
    plotter._edge_feature_angle = EDGE_FEATURE_ANGLE
    plotter._iso_count = ISO_COUNT_DEFAULT
    plotter._iso_axis = 3
    plotter._reduction_mesh = REDUCTION_MESH
    plotter._rot_elev = 0.0
    plotter._is_turntable = SHOW_TURNTABLE
    plotter._needs_update = True
    plotter._fps = 0.0
    plotter._n_points = 0
    plotter._n_faces = 0
    plotter._quality_cache = None
    plotter._quality_cache_n_faces = -1
    plotter._quality_cache_range = None
    plotter._quality_vtk_poly = None
    plotter._is_colorbar = SHOW_COLORBAR
    plotter._is_seq_visible = SHOW_IMAGE_SEQUENCE
    plotter._is_overlay_visible = not getattr(args, 'hide_info', False)
    plotter._overlay_prev_vis = {}
    plotter._mode_msg = ''
    plotter._mode_msg_time = 0.0
    plotter._render_error = ''
    plotter._error_msg = ''
    plotter._error_msg_time = 0.0
    plotter._preload_all = getattr(args, 'preload_all', True)
    plotter._is_np_data = False
    plotter._pt_cloud_size = PT_CLOUD_SIZE_DEFAULT
    plotter._pt_cloud_use_rgb = True
    plotter._pt_cloud_depth = False
    plotter._pt_fog_enabled = POINT_FOG
    plotter._pt_cloud_startup_done = False
    plotter._pt_shader_size = -1
    plotter._pt_color_buf = None
    plotter._pt_fog_gpu = None
    plotter._pt_fog_gpu_base = -1
    plotter._pt_fog_unif_key = None
    plotter._pt_fog_color_key = None
    plotter._pt_normal_color_key = None
    plotter._depth_fog_gpu = None
    plotter._depth_fog_gpu_base = -1
    plotter._depth_fog_gpu_fog = None
    plotter._depth_unif_key = None
    plotter._depth_scalar_key = None
    plotter._pt_size_unif_key = None
    _file_type = getattr(args, '_file_type', 'mesh')
    (
        _startup_axis,
        _rev_x, _rev_y, _rev_z,
        _flip_x, _flip_y, _flip_z,
    ) = resolve_axis_settings(_file_type)
    plotter._axis_swap = _AXIS_SWAP_MAP.get(_startup_axis.upper(), 0)

    _rx = _rev_x ^ _flip_y ^ _flip_z
    _ry = _rev_y ^ _flip_x ^ _flip_z
    _rz = _rev_z ^ _flip_x ^ _flip_y
    plotter._axis_reverse = (_rx, _ry, _rz)
    plotter._actor_cycle_idx = 0
    plotter._special_key_dispatch = {}
    plotter._ctrl_key_dispatch = {}
    plotter._is_audio = False
    plotter._audio_renderer = None

    _apply_startup_mode(plotter)
