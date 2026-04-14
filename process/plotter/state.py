import os
import time

from configs.settings import (
    DEFAULT_GRID, DEFAULT_BBOX, DEFAULT_BACKFACE, DEFAULT_LIGHTING,
    DEFAULT_TURNTABLE, DEFAULT_COLORBAR,
    EDGE_FEATURE_ANGLE,
    ISO_COUNT_DEFAULT, REDUCTION_MESH,
    VTX_SPATIAL_INTERVAL,
    PT_CLOUD_SIZE_DEFAULT, POINT_FOG,
    STARTUP_MODE,
    STARTUP_AXIS,
    STARTUP_REVERSE_X_AXIS, STARTUP_REVERSE_Y_AXIS, STARTUP_REVERSE_Z_AXIS,
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
    'pbr_tex':     0,
    'pbr_tex.tex': 1,
    'pbr_tex.pbr': 2,
}

def _apply_startup_mode(plotter) -> None:
    idx = _SMOOTH_STARTUP_MAP.get(STARTUP_MODE)
    if idx is not None:
        plotter._is_smooth = True
        plotter._smooth_cycle = idx
        if idx == 0:
            plotter._is_lighting = True
            plotter._is_tex = True
            plotter._pbr_with_tex = True
        elif idx == 1:
            plotter._is_tex = True
        else:
            plotter._is_lighting = True
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
    plotter._is_grid = DEFAULT_GRID
    plotter._is_bbox = DEFAULT_BBOX
    plotter._is_isoline = False
    plotter._isoline_visible = False
    plotter._is_iso_only = False
    plotter._is_lighting = DEFAULT_LIGHTING
    plotter._is_backface = DEFAULT_BACKFACE
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
    plotter._is_turntable = DEFAULT_TURNTABLE
    plotter._needs_update = True
    plotter._fps = 0.0
    plotter._n_points = 0
    plotter._n_faces = 0
    plotter._quality_cache = None
    plotter._quality_cache_n_faces = -1
    plotter._quality_cache_range = None
    plotter._quality_vtk_poly = None
    plotter._is_colorbar = DEFAULT_COLORBAR
    plotter._is_overlay_visible = not getattr(args, 'hide_info', False)
    plotter._overlay_prev_vis = {}
    plotter._mode_msg = ''
    plotter._mode_msg_time = 0.0
    plotter._render_error = ''
    plotter._error_msg = ''
    plotter._error_msg_time = 0.0
    plotter._preload_all = getattr(args, 'preload_all', True)
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
    plotter._axis_swap = _AXIS_SWAP_MAP.get(STARTUP_AXIS.upper(), 0)
    plotter._axis_reverse = (
        STARTUP_REVERSE_X_AXIS,
        STARTUP_REVERSE_Y_AXIS,
        STARTUP_REVERSE_Z_AXIS,
    )
    plotter._actor_cycle_idx = 0
    plotter._special_key_dispatch = {}
    plotter._ctrl_key_dispatch = {}
    plotter._is_audio = False
    plotter._audio_renderer = None

    _apply_startup_mode(plotter)
