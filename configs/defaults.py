import psutil as _psutil

# --- Paths ---
INPUT_DIR_ROOT      = './input'
OUTPUT_DIR_ROOT     = './output'
MESH_DIR_ROOT       = f'{INPUT_DIR_ROOT}/mesh'
SEQUENCE_DIR_ROOT   = f'{INPUT_DIR_ROOT}/sequence'
TEXTURE_DIR_ROOT    = f'{INPUT_DIR_ROOT}/texture'
CACHE_DIR_ROOT      = f'{INPUT_DIR_ROOT}/cache'
AUDIO_DIR_ROOT      = f'{INPUT_DIR_ROOT}/audio'
LOG_DIR             = './logs'
HDRI_PATH           = './assets/hdri/pav_studio_03_4k.hdr'

# --- Supported file formats ---
MESH_EXTENSIONS = (
    '.obj', '.ply', '.stl',
    '.vtp', '.vtk',
    '.off', '.glb', '.gltf',
    '.dae', '.3ds', '.byu',
)
TEX_EXTENSIONS  = ('.jpg', '.jpeg', '.png', '.bmp', '.tif', '.tiff', '.tga')
AUDIO_EXTENSIONS = (
    '.wav', '.mp3', '.flac', '.ogg',
    '.aac', '.m4a', '.aif', '.aiff',
)

ABC_CONVERT_FORMAT  = 'obj'   # output format for ABC auto-convert ('obj' or 'ply')

# --- Save format ---
SAVE_FILENAME_DIGITS    = 4       # frame number zero-pad width (####)
SAVE_FILENAME_EXT       = 'png'   # screenshot file extension
SCREENSHOT_SUBDIR       = 'screenshot'

# --- System resources ---
DEFAULT_RESERVED_MEMORY_MB  = 2048  # reserved memory (MB)
DEFAULT_RESERVED_CORES      = 2     # reserved CPU core count
DEFAULT_SYSTEM_USAGE        = 0.80  # max system resource usage ratio

_cpu_count    = _psutil.cpu_count(logical=False) or 1
_usable_cores = max(1, _cpu_count - DEFAULT_RESERVED_CORES)

# --- Frame buffer ---
DEFAULT_PRELOAD_ALL     = True  # preload all frames (prioritizes max playback speed)
DEFAULT_WINDOW_SIZE     = 1500  # sliding window size (must be >= 2 * DEFAULT_PRELOAD_AHEAD)
DEFAULT_PRELOAD_AHEAD   = 1800  # forward prefetch frame count
PRELOAD_BACK_RATIO      = 0.25  # backward prefetch ratio (25% of forward)
EVICT_MEMORY_THRESHOLD  = 0.85  # memory pressure threshold for window shrink (85%)
WORKER_COUNT            = max(1, int(_usable_cores * DEFAULT_SYSTEM_USAGE))
DEFAULT_MESH_WORKERS    = WORKER_COUNT
DEFAULT_TEX_WORKERS     = WORKER_COUNT

# --- Window ---
WINDOW_TITLE         = 'vtkOpenGLMeshViewer'
WINDOW_ASPECT_RATIO  = 1.0   # aspect ratio (e.g. 1.78=16:9, 0.75=4:3, 1.0=square)
WINDOW_WIDTH         = 1024  # window width in pixels
WINDOW_HEIGHT        = round(WINDOW_WIDTH * WINDOW_ASPECT_RATIO)
WINDOW_MONITOR_INDEX = 0

_FONT_BASE_WIDTH = WINDOW_WIDTH
_font_scale      = WINDOW_WIDTH / _FONT_BASE_WIDTH


def _set_fontsize(pt: int) -> int:
    return max(1, round(pt * _font_scale))


# --- Camera ---
CAM_DIST_FACTOR = 3.5
CAM_UP_VECTOR   = (0, 1, 0)
CAM_ZOOM_STEP   = 1.1   # KP_7/9 zoom factor
CAM_PAN_STEP    = 0.05  # KP_1/3 pan ratio (relative to camera distance)
CAM_TRUCK_STEP  = 0.02  # Ctrl+KP truck/pedestal ratio (relative to camera distance)

# --- Render quality ---
RENDER_MSAA_SAMPLES     = 0     # MSAA sample count (0=disabled, 2/4/8/16)
RENDER_FXAA             = True  # FXAA (ignored if MSAA_SAMPLES != 0)
RENDER_LINE_SMOOTHING   = True  # line anti-aliasing
RENDER_POINT_SMOOTHING  = True  # point anti-aliasing
SAVE_ALPHA              = False # transparent background on PNG save (disables MSAA)

# --- Colors ---
COLOR_BG            = '#111111'
COLOR_MESH_DEFAULT  = '#FFFFFF'
COLOR_MESH_ISO      = '#FFFC55'
COLOR_MESH_NO_TEX   = '#FF4444'  # mesh color when texture is missing

# --- Grid & bounding box ---
COLOR_GRID       = '#7A7A7A'
COLOR_BBOX       = '#7A7A7A'
GRID_WIDTH       = 1.0      # grid line width (pixels)
BBOX_WIDTH       = 1.0      # bounding box line width (pixels)
GRID_FONT_FAMILY = 'courier'
UI_FONT_FAMILY   = GRID_FONT_FAMILY

# --- Axis marker ---
AXIS_FONT_SIZE  = _set_fontsize(13)
AXIS_VIEWPORT   = (0, 0, 0.12, 0.12)
AXIS_NAMES      = {0: 'X', 1: 'Y', 2: 'Z'}
AXIS_COLORS     = [(1, 0.4, 0.4), (0.4, 1, 0.4), (0.4, 0.4, 1)]

# --- PBR & HDRI ---
PBR_METALLIC    = 0.00
PBR_ROUGHNESS   = 0.8
PBR_ANISOTROPY  = 0.1
HDRI_INTENSITY  = 0.75
HDRI_ROT_STEP   = 5.0

# --- Startup mode ---
# Options: 'default' | 'wire' | 'smooth' | 'pbr_tex' | 'pbr_tex.tex' |
#          'pbr_tex.pbr' | 'isoline' | 'normal_color' | 'mesh_quality' |
#          'face_normal' | 'depth' | 'edge' | 'vtx'
STARTUP_MODE             = 'pbr_tex'
# Startup mode for point cloud files (auto-detected):
#   'point_rgb'   : vertex color display (default)
#   'point_white' : solid white points
#   'depth'       : depth colormap
STARTUP_MODE_POINT_CLOUD = 'point_rgb'

# --- Startup axis transform ---
# STARTUP_AXIS: initial F5 state ('OFF' | 'YZ' | 'XZ' | 'XY')
# STARTUP_REVERSE_*_AXIS: flip axis sign (applied before swap, in original coordinate space)
# STARTUP_CAM_DEGREE: initial camera azimuth around Y (degrees; positive=right, 0=default)
STARTUP_AXIS            = 'YZ'
STARTUP_REVERSE_X_AXIS  = False
STARTUP_REVERSE_Y_AXIS  = True
STARTUP_REVERSE_Z_AXIS  = False
STARTUP_CAM_DEGREE      = -70

# --- Default state ---
DEFAULT_GRID        = True
DEFAULT_BBOX        = True
DEFAULT_BACKFACE    = True
DEFAULT_LIGHTING    = False
DEFAULT_TEXTURE     = False
DEFAULT_ANIMATION   = True
DEFAULT_SMOOTH      = False
DEFAULT_TURNTABLE   = True
DEFAULT_HIDE_INFO   = False
DEFAULT_COLORBAR    = True

# --- Animation timing ---
TARGET_ANIM_FPS         = 30
UPDATE_INTERVAL         = 0.016    # idle update interval (60 Hz)
UPDATE_INTERVAL_PLAY    = 0.033    # playback update interval (30 Hz)
TURNTABLE_STEP          = 1.0      # auto-turntable rotation step (degrees/frame)

# --- Mesh normalization ---
NORM_SIZE       = 1.0
MAX_FRAME_SKIP  = 1

# --- Mesh reduction ---
REDUCTION_MESH      = 1.0   # 1.0=original, 0.1=maximum reduction
REDUCTION_MESH_STEP = 0.05

# --- Auto-decimation thresholds ---
AUTO_DECIMATE_THRESHOLD = 100_000   # face count threshold for auto-decimation
AUTO_DECIMATE_MAX_CELLS = 200_000   # target face count for ratio calculation
AUTO_DECIMATE_MAX_RATIO = 0.1       # maximum removal ratio cap (0~1)

# --- Isoline contour face limit ---
ISOLINE_CONTOUR_MAX_FACES = 50_000

# --- Point cloud subsampling thresholds ---
PT_SUBSAMPLE_THRESHOLD  = 500_000   # auto-subsampling trigger point count
PT_SUBSAMPLE_TARGET     = 300_000   # target point count after subsampling

# --- Occluder polygon offset (z-fighting prevention) ---
# factor=0: removes slope-dependent offset -> prevents grid z-fighting
# units=8:  constant small retreat -> iso/wire lines always in front of occluder
OFFSET_MESH_BACK    = (0.0, 8.0)

# --- Isoline ---
COLOR_ISO_LINE      = 'plasma'   # hex color or matplotlib cmap name
WIDTH_ISO_LINE      = 2.5
TYPE_TUBE           = False
ISO_COUNT_DEFAULT   = 30
ISO_COUNT_STEP      = 1
# Geometric offset along mesh normals to prevent z-fighting
# (VTK 9.x does not support GL_POLYGON_OFFSET_LINE)
ISO_NORMAL_OFFSET   = 2e-3

# --- Wireframe ---
COLOR_WIREFRAME = 'gist_ncar'    # hex color or matplotlib cmap name
WIDTH_WIREFRAME = 0.111

# --- Edge extract ---
COLOR_EDGE              = 'plasma'  # hex color or matplotlib cmap name
WIDTH_EDGE              = 1.0
EDGE_FEATURE_ANGLE      = 13.5      # dihedral angle threshold (degrees)
EDGE_FEATURE_ANGLE_STEP = 2.5

# --- Depth ---
COLOR_DEPTH             = 'twilight'  # hex color or matplotlib cmap name
COLOR_PT_CLOUD_DEPTH    = 'binary_r'  # point cloud depth colormap
PT_CLOUD_DEPTH_CONTRAST = 3.0         # depth contrast (1.0=linear, higher=sharper B/W)
POINT_FOG               = True        # fog effect for all point cloud modes
POINT_FOG_START         = 0.7         # fog start (0~1); below=fully visible, above=fade to bg
DEPTH_AXIS_DEFAULT      = 3           # 0=X 1=Y 2=Z 3=camera view direction
DEPTH_SHADING_FLAT      = True
DEPTH_ENABLE_LIGHTING   = False

# --- Normal color ---
NORMAL_COLOR_ENABLE_LIGHTING = False

# --- Face normal ---
FNORMAL_SPATIAL_INTERVAL    = 0.05  # minimum world-space spacing between arrows
FNORMAL_CMAP                = 'viridis'
FNORMAL_MESH_OPACITY        = 1.0
FNORMAL_SCALE               = 0.05  # arrow glyph length (world units)
FNORMAL_TIP_LENGTH          = 0.35
FNORMAL_TIP_RADIUS          = 0.1
FNORMAL_SHAFT_RADIUS        = 0.03
FNORMAL_TIP_RESOLUTION      = 6
FNORMAL_SHAFT_RESOLUTION    = 4

# --- Mesh quality ---
COLOR_MESH_QUALITY  = 'RdYlGn'           # red=poor, green=good
MESH_QUALITY_METRIC = 'scaled_jacobian'  # VTK mesh quality measure

# --- Point cloud ---
PT_CLOUD_SIZE_DEFAULT     = 3     # default point size (pixels)
PT_CLOUD_SIZE_POINT_WHITE = 1     # point size on entry to point_white mode
PT_CLOUD_SIZE_DEPTH       = 4     # point size on entry to depth mode
PT_CLOUD_SIZE_STEP        = 1     # increment/decrement step (pixels)
PT_CLOUD_SIZE_MIN         = 1     # minimum point size (pixels)
PT_CLOUD_SIZE_MAX         = 20    # maximum point size (pixels)
PT_CLOUD_SHADER_SCALE     = 300.0 # distance-based sizing: gl_PointSize = clamp(SCALE/dist, MIN, MAX)
PT_CLOUD_SHADER_SIZE_MIN  = 1.0   # shader minimum point size
PT_CLOUD_SHADER_SIZE_MAX  = 12.0  # shader maximum point size

# --- Vertex label ---
VTX_SPATIAL_INTERVAL    = 0.04
VTX_SPATIAL_STEP        = 0.005
VTX_SCREEN_INTERVAL     = 10     # minimum screen-space spacing (pixels)
VTX_LABEL_FONT_SIZE     = _set_fontsize(10)
VTX_LABEL_COLOR         = '#FFFFFF'
VTX_POINT_SIZE          = 6
VTX_POINT_COLOR         = '#FF0000'
VTX_PICK_SIZE           = 14
VTX_PICK_COLOR          = '#FFFF00'

# --- Status text (top-left) ---
UI_STATUS_FONT_SIZE     = _set_fontsize(15)
UI_STATUS_LINE_SPACING  = 1.10
UI_STATUS_COLOR         = '#DADADA'
UI_STATUS_PAD_PX        = 10
UI_STATUS_PAD_PY        = 15

# --- System info monitor ---
UI_SYSINFO_FONT_SIZE    = _set_fontsize(15)
UI_SYSINFO_COLOR        = '#DADADA'
UI_SYSINFO_PAD_PX       = UI_STATUS_PAD_PX
UI_SYSINFO_PAD_PY       = 10

# --- Log overlay (bottom-left) ---
UI_LOG_FONT_SIZE    = _set_fontsize(12)
UI_LOG_COLOR        = '#686868'
UI_LOG_ERROR_COLOR  = '#FF0000'  # error log color (fixed, theme-independent)
UI_LOG_PAD_PX       = 10
UI_LOG_PAD_PY       = 10

# --- Mode text (top-right) ---
UI_MODE_FONT_SIZE   = _set_fontsize(15)
UI_MODE_COLOR       = '#FFC400'
UI_MODE_BACKGROUND  = '#FD1212'
UI_MODE_PAD_PX      = UI_STATUS_PAD_PY
UI_MODE_PAD_PY      = UI_MODE_PAD_PX
MODE_MSG_DURATION   = 3.0
ERROR_MSG_DURATION  = 3.0

# --- Help overlay ---
UI_HELP_FONT_SIZE   = _set_fontsize(14)
UI_HELP_COLOR       = '#DDDDDD'
UI_HELP_BG_OPACITY  = 0.75
UI_HELP_TEXT_W      = round(310 * _font_scale)
UI_HELP_TEXT_H      = round(430 * _font_scale)
UI_HELP_POS_X       = (WINDOW_WIDTH  - UI_HELP_TEXT_W) // 2
UI_HELP_POS_Y       = (WINDOW_HEIGHT - UI_HELP_TEXT_H) // 2

# --- Colorbar ---
UI_COLORBAR_WIDTH           = 0.10
UI_COLORBAR_HEIGHT          = 0.40
UI_COLORBAR_POS_X           = 0.925
UI_COLORBAR_POS_Y           = 0.30
UI_COLORBAR_FONT_FAMILY     = 'courier'
UI_COLORBAR_TITLE_FONT_SIZE = 0
UI_COLORBAR_LABEL_FONT_SIZE = _set_fontsize(10)
UI_COLORBAR_TITLE_COLOR     = '#DADADA'
UI_COLORBAR_LABEL_COLOR     = '#DADADA'
UI_COLORBAR_NLABELS         = 5
UI_COLORBAR_BAR_RATIO       = 0.19

# --- Sequence image overlay ---
SEQ_SIZE_W          = 0.15   # viewport width ratio (height auto-calculated from image aspect)
SEQ_PAD_RIGHT_PX    = 10     # right padding (pixels)
SEQ_PAD_BOTTOM_PX   = 10     # bottom padding (pixels)
SEQ_IMAGE_EXTS      = ('.png', '.jpg', '.jpeg', '.bmp')

# --- Logging ---
LOG_FORMAT      = '%(asctime)s | %(levelname)-8s | %(name)s: %(message)s'
LOG_MSEC_FORMAT = '%s.%03d'

# --- Audio mode ---
# Startup render mode: 'ISOLINE' | 'MESH' | 'WIREFRAME'
STARTUP_AUDIO_MODE      = 'ISOLINE'
AUDIO_ISO_AXIS          = 'Y'    # contour axis ('X'|'Y'|'Z'|'CAM')
AUDIO_COLOR_AXIS        = 'Y'    # color axis   ('X'|'Y'|'Z'|'CAM')
AUDIO_ISO_COUNT_DEFAULT = 20

# --- Audio colormaps ---
AUDIO_ISOLINE_CMAP   = 'gist_rainbow'
AUDIO_WIREFRAME_CMAP = 'jet'
AUDIO_MESH_CMAP      = 'plasma'
AUDIO_DEPTH_CMAP     = 'twilight'
AUDIO_EDGE_CMAP      = 'viridis'
AUDIO_QUALITY_CMAP   = 'RdYlGn'
AUDIO_FNORMAL_CMAP   = 'plasma'

# --- Audio grid & display ---
AUDIO_GRID_Y_MAX            = 100.0
AUDIO_FREQ_NORM_MAX         = 100.0
AUDIO_COLOR_GRID            = COLOR_GRID
AUDIO_COLOR_BBOX            = COLOR_GRID
AUDIO_AXIS_LABEL_FONT_SIZE  = _set_fontsize(12)
AUDIO_GRID_TEXT_COLOR       = COLOR_GRID

# --- Audio preprocessing ---
AUDIO_TARGET_FPS        = 30
AUDIO_FREQ_SAMPLES      = 60        # frequency bins (X-axis resolution)
AUDIO_TIME_RANGE        = 3.0       # time window (seconds)
AUDIO_FOCUS_FREQ_RANGE  = (5, 150)  # STFT frequency bin range of interest
AUDIO_REFERENCE_FRAMES  = 5         # frames used for noise floor estimation
AUDIO_QUIET_THRESHOLD   = 10.0      # silence/low-amplitude flattening threshold (dB)
AUDIO_MIN_DB_THRESHOLD  = 15.0      # per-frame dB lower cutoff
AUDIO_MIN_MESH_VALUE    = 10        # amplitude values below this are set to 0

# --- Audio geometry ---
AUDIO_FADE_WIDTH            = 0.01   # boundary fade ratio (0=disabled)
AUDIO_MESH_SMOOTHING_ITERS  = 40     # Taubin smoothing iterations
AUDIO_MESH_Y_OFFSET         = -1.0   # Y offset correction after smoothing
AUDIO_MESH_Y_CUTOFF         = 1.0    # Y values below this are flattened to 0

# --- Audio style ---
AUDIO_ISOLINE_WIDTH             = 3.0
AUDIO_ISO_OFFSET                = 0.5   # Y-axis shift for iso lines (z-fighting prevention)
AUDIO_WIREFRAME_LINE_WIDTH      = 3.0
AUDIO_EDGE_FEATURE_ANGLE        = 15.0  # edge extraction angle threshold (degrees)
AUDIO_FNORMAL_SPATIAL_INTERVAL  = 5.0   # minimum spacing between normal arrows (grid units)
AUDIO_FNORMAL_SCALE             = 5.0   # normal arrow glyph scale
AUDIO_SEEK_STEP                 = 30    # seek frames per left/right key press

# --- Audio camera defaults ---
AUDIO_CAM_POSITION    = (350, 300, 350)
AUDIO_CAM_FOCAL_POINT = (50, 50, 50)
AUDIO_CAM_UP          = (0, 1, 0)

# --- Audio recording ---
AUDIO_RECORD_SUBDIR      = 'screenshot'
AUDIO_MAX_RECORD_WORKERS = WORKER_COUNT
