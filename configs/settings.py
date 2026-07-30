from configs.theme import (
    apply_theme as _apply_theme,
    make_fontsize_fn as _make_fontsize_fn,
)
from configs.system_resources import (
    get_usable_cpu, get_io_workers, compute_window_size,
)
from configs.settings_mesh import *          # noqa: F401, F403
from configs.settings_point_cloud import *   # noqa: F401, F403
from configs.settings_audio import *         # noqa: F401, F403
from configs.settings_np_data import *       # noqa: F401, F403

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
    '.npy', '.npz',
)
TEX_EXTENSIONS  = ('.jpg', '.jpeg', '.png', '.bmp', '.tif', '.tiff', '.tga')
AUDIO_EXTENSIONS = (
    '.wav', '.mp3', '.flac', '.ogg',
    '.aac', '.m4a', '.aif', '.aiff',
)

ABC_CONVERT_FORMAT  = 'obj'

# --- Save format ---
# SAVE_EXT: output extension, overridable with '-f'
#   'mp4' / 'mov' -> ffmpeg pipe video encoding (process/record)
#   'png' / 'jpg' -> image sequence
SAVE_EXT                = 'mp4'
SAVE_IMAGE_EXTS         = ('png', 'jpg', 'jpeg')
SAVE_VIDEO_EXTS         = ('mp4', 'mov')

SAVE_FILENAME_DIGITS    = 4
SAVE_FILENAME_EXT       = 'png'
SCREENSHOT_EXT          = 'png'  # '`' screenshot is always an image
SAVE_PNG_COMPRESSION    = 3
SAVE_JPEG_QUALITY       = 95
SAVE_PBO_ENABLED        = True
SCREENSHOT_SUBDIR       = 'screenshot'

# SAVE_ENCODE_WORKERS: parallel workers for image sequence encoding.
#   cv2.imwrite releases the GIL; video uses a single ffmpeg pipe.
SAVE_ENCODE_WORKERS     = get_usable_cpu(2, 0.80)

# AVOID_NAME_COLLISION: add '_01', '_02' surfix instead of overwriting
AVOID_NAME_COLLISION    = True
# SAVE_MODE_FILENAME: append the active render mode to the filename
#   night_of_fire.mp4 -> night_of_fire_isoline.mp4
SAVE_MODE_FILENAME      = True

# --- Video encoding (used when SAVE_EXT is in SAVE_VIDEO_EXTS) ---
FFMPEG_BIN              = 'ffmpeg'
SAVE_VIDEO_CODEC        = 'libx264'     # h264
SAVE_VIDEO_FASTSTART    = True          # mp4 moov atom first (streaming)
SAVE_VIDEO_LOG_LEVEL    = 'error'       # ffmpeg -loglevel

# SAVE_QUALITY: default for '-q'. One of SAVE_QUALITY_PRESETS.
#   crf     0=lossless, lower is better (18=visually lossless)
#   pix_fmt yuv420p=chroma subsampled / yuv444p=no subsampling
#           thin elements (grid lines, overlay text) blur on yuv420p
SAVE_QUALITY            = 'high'
SAVE_QUALITY_PRESETS    = {
    'low':  {
        'codec': 'libx264', 'crf': 28,
        'preset': 'veryfast', 'pix_fmt': 'yuv420p',
    },
    'high': {
        'codec': 'libx264', 'crf': 16,
        'preset': 'medium', 'pix_fmt': 'yuv444p',
    },
    'raw':  {
        'codec': 'libx264', 'crf': 0,
        'preset': 'medium', 'pix_fmt': 'yuv444p',
    },
}

# --- System resources ---
DEFAULT_RESERVED_MEMORY_MB  = 2048
DEFAULT_RESERVED_CORES      = 2
DEFAULT_SYSTEM_USAGE        = 0.80

# --- Frame buffer ---
DEFAULT_PRELOAD_ALL     = True
DEFAULT_MAX_WINDOW_SIZE = 1500
DEFAULT_WINDOW_SIZE     = compute_window_size(
    DEFAULT_RESERVED_MEMORY_MB, DEFAULT_SYSTEM_USAGE,
)
DEFAULT_PRELOAD_AHEAD   = int(DEFAULT_WINDOW_SIZE * 0.875)
PRELOAD_BACK_RATIO      = 0.50
EVICT_MEMORY_THRESHOLD  = 0.875
WORKER_COUNT            = get_usable_cpu(DEFAULT_RESERVED_CORES, DEFAULT_SYSTEM_USAGE)
IO_WORKER_COUNT         = get_io_workers(DEFAULT_SYSTEM_USAGE)

# --- Window ---
WINDOW_TITLE         = 'vtkOpenGLMeshViewer'
WINDOW_ASPECT_RATIO  = 1.0
WINDOW_WIDTH         = 1024
WINDOW_HEIGHT        = round(WINDOW_WIDTH * WINDOW_ASPECT_RATIO)
WINDOW_MONITOR_INDEX = 0

_font_scale   = 1.0
_set_fontsize = _make_fontsize_fn(_font_scale)

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
COLOR_BG         = _apply_theme('#111111')
MESH_MATTE_COLOR = None

# --- Grid & bounding box ---
COLOR_GRID       = _apply_theme('#7A7A7A')
COLOR_BBOX       = _apply_theme('#7A7A7A')
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

# --- Overlay master switches ---
# False skips actor creation entirely, so the toggle key stays inert.
# Use SHOW_HIDE_INFO / --hide-info to merely start hidden instead.
DISPLAY_STATUS      = True  # status text (',' key)
DISPLAY_SYSINFO     = True  # CPU/MEM/GPU line and its sampler thread
DISPLAY_MODE        = True  # mode and error messages
DISPLAY_LOG         = True  # log overlay ('.' key)
DISPLAY_COLORBAR    = True  # colormap legend
DISPLAY_HELP        = True  # help overlay ('h' key)
DISPLAY_SEQUENCE    = True  # image sequence overlay ("'" key)
DISPLAY_AXES        = True  # orientation axes marker

# --- Overlay font ---
# The first family installed on the system wins (resolved with fc-match).
FONT_PRIORITY = (
    'Ubuntu Sans Mono',
    'DejaVu Sans Mono',
    'Noto Sans Mono',
    'Liberation Mono',
    'monospace',
)

# --- Status text (top-left) ---
UI_STATUS_FONT_SIZE     = _set_fontsize(15)
UI_STATUS_LINE_SPACING  = 1.10
UI_STATUS_COLOR         = _apply_theme('#DADADA')
UI_STATUS_PAD_PX        = 10
UI_STATUS_PAD_PY        = 15

# --- System info monitor ---
UI_SYSINFO_FONT_SIZE    = _set_fontsize(15)
UI_SYSINFO_COLOR        = _apply_theme('#DADADA')
UI_SYSINFO_PAD_PX       = UI_STATUS_PAD_PX
UI_SYSINFO_PAD_PY       = UI_STATUS_PAD_PX

# --- Log overlay (bottom-left) ---
UI_LOG_FONT_SIZE    = _set_fontsize(12)
UI_LOG_COLOR        = _apply_theme('#686868')
UI_LOG_ERROR_COLOR  = '#FF0000'
UI_LOG_PAD_PX       = 10
UI_LOG_PAD_PY       = 10
# Overlay-only log format (no name:lineno; the file log keeps its own)
UI_LOG_FORMAT       = '%(asctime)s | %(levelname)-8s | %(message)s'
# UI_LOG_MAX_CHARS: 0 = derive from window width and font size
UI_LOG_MAX_CHARS    = 0
UI_LOG_MIN_CHARS    = 20
UI_LOG_ELLIPSIS     = '…'

# --- Mode text (top-right) ---
UI_MODE_FONT_SIZE   = _set_fontsize(15)
UI_MODE_COLOR       = _apply_theme('#FFC400')
UI_MODE_BACKGROUND  = _apply_theme('#FD1212')
UI_MODE_PAD_PX      = UI_STATUS_PAD_PY
UI_MODE_PAD_PY      = UI_MODE_PAD_PX
MODE_MSG_DURATION   = 3.0
ERROR_MSG_DURATION  = 3.0

# --- Help overlay ---
UI_HELP_FONT_SIZE   = _set_fontsize(14)
UI_HELP_COLOR       = _apply_theme('#DDDDDD')
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
UI_COLORBAR_TITLE_COLOR     = _apply_theme('#DADADA')
UI_COLORBAR_LABEL_COLOR     = _apply_theme('#DADADA')
UI_COLORBAR_NLABELS         = 5
UI_COLORBAR_BAR_RATIO       = 0.19

# --- Sequence image overlay ---
SEQ_SIZE_W          = 0.15
SEQ_PAD_RIGHT_PX    = 10
SEQ_PAD_BOTTOM_PX   = 10
SEQ_IMAGE_EXTS      = ('.png', '.jpg', '.jpeg', '.bmp')

# --- Logging ---
LOG_FORMAT      = '%(asctime)s | %(levelname)-8s | %(name)s:%(lineno)d - %(message)s'
LOG_MSEC_FORMAT = '%s.%03d'


def resolve_axis_settings(file_type):
    _overrides = {
        'mesh': (
            MESH_STARTUP_AXIS,
            MESH_STARTUP_REVERSE_X_AXIS,
            MESH_STARTUP_REVERSE_Y_AXIS,
            MESH_STARTUP_REVERSE_Z_AXIS,
            MESH_FLIP_OBJECT_X,
            MESH_FLIP_OBJECT_Y,
            MESH_FLIP_OBJECT_Z,
        ),
        'point_cloud': (
            PT_STARTUP_AXIS,
            PT_STARTUP_REVERSE_X_AXIS,
            PT_STARTUP_REVERSE_Y_AXIS,
            PT_STARTUP_REVERSE_Z_AXIS,
            PT_FLIP_OBJECT_X,
            PT_FLIP_OBJECT_Y,
            PT_FLIP_OBJECT_Z,
        ),
        'np_data': (
            NP_STARTUP_AXIS,
            NP_STARTUP_REVERSE_X_AXIS,
            NP_STARTUP_REVERSE_Y_AXIS,
            NP_STARTUP_REVERSE_Z_AXIS,
            NP_FLIP_OBJECT_X,
            NP_FLIP_OBJECT_Y,
            NP_FLIP_OBJECT_Z,
        ),
        'audio': (
            AUDIO_STARTUP_AXIS,
            AUDIO_STARTUP_REVERSE_X_AXIS,
            AUDIO_STARTUP_REVERSE_Y_AXIS,
            AUDIO_STARTUP_REVERSE_Z_AXIS,
            AUDIO_FLIP_OBJECT_X,
            AUDIO_FLIP_OBJECT_Y,
            AUDIO_FLIP_OBJECT_Z,
        ),
    }
    _defaults = (
        STARTUP_AXIS,
        STARTUP_REVERSE_X_AXIS,
        STARTUP_REVERSE_Y_AXIS,
        STARTUP_REVERSE_Z_AXIS,
        FLIP_OBJECT_X,
        FLIP_OBJECT_Y,
        FLIP_OBJECT_Z,
    )
    overrides = _overrides.get(file_type, (None,) * 7)
    return tuple(
        o if o is not None else d
        for o, d in zip(overrides, _defaults)
    )
