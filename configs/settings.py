from core.theme import (                     # noqa: F401
    apply_theme, make_fontsize_fn,
)
from configs.system_resources import (  # noqa: F401
    get_usable_cpu, get_io_workers, compute_window_size,
)

from configs.settings_system import *    # noqa: F401, F403
from configs.settings_window import *    # noqa: F401, F403
from configs.settings_camera import *    # noqa: F401, F403
from configs.settings_render import *    # noqa: F401, F403
from configs.settings_font import *      # noqa: F401, F403
from configs.settings_color import *     # noqa: F401, F403
from configs.settings_overlay import *   # noqa: F401, F403

from configs.settings_mesh import *          # noqa: F401, F403
from configs.settings_point_cloud import *   # noqa: F401, F403
from configs.settings_audio import *         # noqa: F401, F403
from configs.settings_np_data import *       # noqa: F401, F403

from core.theme import apply_theme as _apply_theme  # noqa: F401
from configs.settings_font import (      # noqa: F401
    _font_scale, _set_fontsize,
)

INPUT_DIR_ROOT      = './input'
OUTPUT_DIR_ROOT     = './output'
LOG_DIR             = './logs'
SCREENSHOT_SUBDIR   = 'screenshot'
MESH_DIR_ROOT       = f'{INPUT_DIR_ROOT}/mesh'
SEQUENCE_DIR_ROOT   = f'{INPUT_DIR_ROOT}/sequence'
TEXTURE_DIR_ROOT    = f'{INPUT_DIR_ROOT}/texture'
CACHE_DIR_ROOT      = f'{INPUT_DIR_ROOT}/cache'
AUDIO_DIR_ROOT      = f'{INPUT_DIR_ROOT}/audio'

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

SAVE_EXT                = 'mp4'
SAVE_IMAGE_EXTS         = ('png', 'jpg', 'jpeg')
SAVE_VIDEO_EXTS         = ('mp4', 'mov')

SAVE_FILENAME_DIGITS    = 4
SCREENSHOT_EXT          = 'png'
SAVE_PNG_COMPRESSION    = 0
SAVE_JPEG_QUALITY       = 80
SAVE_ALPHA              = False
SAVE_PBO_ENABLED        = True

SAVE_SETTING_LOG        = False

SAVE_LIVE_PREFIX        = 'liveRec_'

SAVE_ENCODE_WORKERS     = get_usable_cpu(2, 0.80)

AVOID_NAME_COLLISION    = True

SAVE_MODE_FILENAME      = True

FFMPEG_BIN              = 'ffmpeg'
SAVE_VIDEO_CODEC        = 'libx264'
SAVE_VIDEO_FASTSTART    = True
SAVE_VIDEO_LOG_LEVEL    = 'error'

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

LOG_FORMAT      = '%(asctime)s | %(levelname)-8s | %(name)s:%(lineno)d - %(message)s'
LOG_MSEC_FORMAT = '%s.%03d'
