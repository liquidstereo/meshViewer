from configs.theme import (
    apply_theme as _apply_theme,
    make_fontsize_fn as _make_fontsize_fn,
)

_font_scale   = 1.0
_set_fontsize = _make_fontsize_fn(_font_scale)

HDRI_PATH   = './assets/hdri/pav_studio_03_4k.hdr'
HDRI_ENABLE = True

COLOR_MESH_DEFAULT  = _apply_theme('#FFFFFF')
COLOR_MESH_ISO      = _apply_theme('#FFFC55')
COLOR_MESH_NO_TEX   = _apply_theme('#FF4444')

PBR_METALLIC    = 0.00
PBR_ROUGHNESS   = 0.8
PBR_ANISOTROPY  = 0.1
HDRI_INTENSITY  = 0.75
HDRI_ROT_STEP   = 5.0

STARTUP_MODE    = 'default'

DEFAULT_TEXTURE = False
DEFAULT_SMOOTH  = False

REDUCTION_MESH      = 1.0
REDUCTION_MESH_STEP = 0.05

AUTO_DECIMATE_THRESHOLD = 100_000
AUTO_DECIMATE_MAX_CELLS = 200_000
AUTO_DECIMATE_MAX_RATIO = 0.1

ISOLINE_CONTOUR_MAX_FACES = 50_000

OFFSET_MESH_BACK    = (0.0, 8.0)

COLOR_ISO_LINE      = 'plasma'
WIDTH_ISO_LINE      = 2.5
TYPE_TUBE           = False
ISO_COUNT_DEFAULT   = 30
ISO_COUNT_STEP      = 1

ISO_NORMAL_OFFSET   = 2e-3

COLOR_WIREFRAME = 'gist_ncar'
WIDTH_WIREFRAME = 0.111

COLOR_EDGE              = 'plasma'
WIDTH_EDGE              = 1.0
EDGE_FEATURE_ANGLE      = 13.5
EDGE_FEATURE_ANGLE_STEP = 2.5

COLOR_DEPTH           = 'twilight'
DEPTH_AXIS_DEFAULT    = 3
DEPTH_SHADING_FLAT    = True
DEPTH_ENABLE_LIGHTING = False

NORMAL_COLOR_ENABLE_LIGHTING = False

FNORMAL_SPATIAL_INTERVAL    = 0.05
FNORMAL_CMAP                = 'viridis'
FNORMAL_MESH_OPACITY        = 1.0
FNORMAL_SCALE               = 0.05
FNORMAL_TIP_LENGTH          = 0.35
FNORMAL_TIP_RADIUS          = 0.1
FNORMAL_SHAFT_RADIUS        = 0.03
FNORMAL_TIP_RESOLUTION      = 6
FNORMAL_SHAFT_RESOLUTION    = 4

COLOR_MESH_QUALITY  = 'RdYlGn'
MESH_QUALITY_METRIC = 'scaled_jacobian'

VTX_SPATIAL_INTERVAL    = 0.04
VTX_SPATIAL_STEP        = 0.005
VTX_SCREEN_INTERVAL     = 10
VTX_LABEL_FONT_SIZE     = _set_fontsize(10)
VTX_LABEL_COLOR         = _apply_theme('#FFFFFF')
VTX_POINT_SIZE          = 6
VTX_POINT_COLOR         = _apply_theme('#FF0000')
VTX_PICK_SIZE           = 14
VTX_PICK_COLOR          = _apply_theme('#FFFF00')
