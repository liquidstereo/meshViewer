import psutil as _psutil
from configs.settings_mesh import *          # noqa: F401, F403
from configs.settings_point_cloud import *   # noqa: F401, F403
from configs.settings_audio import *         # noqa: F401, F403

# --- Paths ---
INPUT_DIR_ROOT      = './input'
OUTPUT_DIR_ROOT     = './output'
MESH_DIR_ROOT       = f'{INPUT_DIR_ROOT}/mesh'
SEQUENCE_DIR_ROOT   = f'{INPUT_DIR_ROOT}/sequence'
TEXTURE_DIR_ROOT    = f'{INPUT_DIR_ROOT}/texture'
CACHE_DIR_ROOT      = f'{INPUT_DIR_ROOT}/cache'
AUDIO_DIR_ROOT      = f'{INPUT_DIR_ROOT}/audio'
LOG_DIR             = './logs'

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

ABC_CONVERT_FORMAT  = 'obj'

# --- Save format ---
SAVE_FILENAME_DIGITS    = 4
SAVE_FILENAME_EXT       = 'png'
SAVE_PNG_COMPRESSION    = 3
SAVE_JPEG_QUALITY       = 95
SAVE_PBO_ENABLED        = True
SCREENSHOT_SUBDIR       = 'screenshot'

# --- System resources ---
DEFAULT_RESERVED_MEMORY_MB  = 2048
DEFAULT_RESERVED_CORES      = 2
DEFAULT_SYSTEM_USAGE        = 0.80

_cpu_count    = _psutil.cpu_count(logical=False) or 1
_usable_cores = max(1, _cpu_count - DEFAULT_RESERVED_CORES)
_total_ram_mb = _psutil.virtual_memory().total / (1024 ** 2)
_avail_ram_mb = max(
    1024,
    (_total_ram_mb - DEFAULT_RESERVED_MEMORY_MB) * DEFAULT_SYSTEM_USAGE,
)

# --- Frame buffer ---
DEFAULT_PRELOAD_ALL     = True
DEFAULT_MAX_WINDOW_SIZE = 1500
DEFAULT_WINDOW_SIZE     = max(DEFAULT_MAX_WINDOW_SIZE, int(_avail_ram_mb / 12))
DEFAULT_PRELOAD_AHEAD   = round(DEFAULT_WINDOW_SIZE * 0.875)
PRELOAD_BACK_RATIO      = 0.50
EVICT_MEMORY_THRESHOLD  = 0.875
WORKER_COUNT            = max(1, int(_usable_cores * DEFAULT_SYSTEM_USAGE))

# --- Window ---
WINDOW_TITLE         = 'vtkOpenGLMeshViewer'
WINDOW_ASPECT_RATIO  = 1.0
WINDOW_WIDTH         = 1024
WINDOW_HEIGHT        = round(WINDOW_WIDTH * WINDOW_ASPECT_RATIO)
WINDOW_MONITOR_INDEX = 0

_font_scale = 1.0


def _set_fontsize(pt: int) -> int:
    return max(1, round(pt * _font_scale))


# --- Camera ---
CAM_DIST_FACTOR = 3.5
CAM_UP_VECTOR   = (0, 1, 0)
CAM_ZOOM_STEP   = 1.1
CAM_PAN_STEP    = 0.05
CAM_TRUCK_STEP  = 0.02

# --- Render quality ---
RENDER_MSAA_SAMPLES     = 8
RENDER_FXAA             = False
RENDER_LINE_SMOOTHING   = True
RENDER_POINT_SMOOTHING  = True
SAVE_ALPHA              = False

# --- Colors ---
COLOR_BG         = '#111111'
MESH_MATTE_COLOR = None

# --- Grid & bounding box ---
COLOR_GRID       = '#7A7A7A'
COLOR_BBOX       = '#7A7A7A'
GRID_WIDTH       = 1.0
BBOX_WIDTH       = 1.0
GRID_FONT_FAMILY = 'courier'
UI_FONT_FAMILY   = GRID_FONT_FAMILY

# --- Axis marker ---
AXIS_FONT_SIZE  = _set_fontsize(13)
AXIS_VIEWPORT   = (0, 0, 0.12, 0.12)
AXIS_NAMES      = {0: 'X', 1: 'Y', 2: 'Z'}
AXIS_COLORS     = [(1, 0.4, 0.4), (0.4, 1, 0.4), (0.4, 0.4, 1)]

# --- Startup axis transform ---
STARTUP_AXIS            = 'YZ'
STARTUP_REVERSE_X_AXIS  = False
STARTUP_REVERSE_Y_AXIS  = True
STARTUP_REVERSE_Z_AXIS  = False
FLIP_OBJECT_X           = False
FLIP_OBJECT_Y           = False
FLIP_OBJECT_Z           = False
STARTUP_CAM_DEGREE      = -70
STARTUP_CAM_POSITION    = None
STARTUP_FOCAL_LENGTH    = None
STARTUP_ZOOM            = None

# --- Default state ---
SHOW_GRID        = True
SHOW_BBOX        = True
SHOW_BACKFACE    = True
SHOW_LIGHTING    = False
SHOW_ANIMATION   = True
SHOW_TURNTABLE   = True
SHOW_HIDE_INFO   = False
SHOW_COLORBAR       = True
SHOW_IMAGE_SEQUENCE = False
SHOW_MESH           = True

# --- Animation timing ---
TARGET_ANIM_FPS         = 30
UPDATE_INTERVAL         = 0.016
UPDATE_INTERVAL_PLAY    = 0.033
TURNTABLE_STEP          = 1.0

# --- Mesh normalization ---
NORM_SIZE       = 1.0
MAX_FRAME_SKIP  = 1

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
UI_SYSINFO_PAD_PY       = UI_STATUS_PAD_PX

# --- Log overlay (bottom-left) ---
UI_LOG_FONT_SIZE    = _set_fontsize(12)
UI_LOG_COLOR        = '#686868'
UI_LOG_ERROR_COLOR  = '#FF0000'
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
SEQ_SIZE_W          = 0.15
SEQ_PAD_RIGHT_PX    = 10
SEQ_PAD_BOTTOM_PX   = 10
SEQ_IMAGE_EXTS      = ('.png', '.jpg', '.jpeg', '.bmp')

# --- Logging ---
LOG_FORMAT      = '%(asctime)s | %(levelname)-8s | %(name)s:%(lineno)d: %(message)s'
LOG_MSEC_FORMAT = '%s.%03d'
