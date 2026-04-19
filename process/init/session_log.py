import os
import logging
from datetime import datetime

from configs.settings import (
    WINDOW_WIDTH, WINDOW_HEIGHT, WINDOW_ASPECT_RATIO,
    TARGET_ANIM_FPS, DEFAULT_ANIMATION,
    DEFAULT_TURNTABLE, TURNTABLE_STEP, MAX_FRAME_SKIP,
    RENDER_MSAA_SAMPLES, RENDER_FXAA,
    RENDER_LINE_SMOOTHING, RENDER_POINT_SMOOTHING,
    SAVE_ALPHA, SAVE_FILENAME_EXT, SAVE_PBO_ENABLED,
    STARTUP_AXIS,
    STARTUP_REVERSE_X_AXIS, STARTUP_REVERSE_Y_AXIS, STARTUP_REVERSE_Z_AXIS,
    FLIP_OBJECT_X, FLIP_OBJECT_Y, FLIP_OBJECT_Z,
    CAM_DIST_FACTOR, STARTUP_CAM_DEGREE,
    STARTUP_CAM_POSITION, STARTUP_FOCAL_LENGTH, STARTUP_ZOOM,
    DEFAULT_GRID, DEFAULT_BBOX, DEFAULT_BACKFACE, DEFAULT_LIGHTING,
    WORKER_COUNT,

    STARTUP_MODE, DEFAULT_TEXTURE, DEFAULT_SMOOTH,
    HDRI_ENABLE, PBR_METALLIC, PBR_ROUGHNESS,
    REDUCTION_MESH, AUTO_DECIMATE_THRESHOLD, AUTO_DECIMATE_MAX_CELLS,
    ISOLINE_CONTOUR_MAX_FACES,
    ISO_COUNT_DEFAULT, COLOR_ISO_LINE, WIDTH_ISO_LINE,
    COLOR_WIREFRAME, WIDTH_WIREFRAME,
    EDGE_FEATURE_ANGLE, DEPTH_AXIS_DEFAULT, MESH_QUALITY_METRIC,

    STARTUP_MODE_POINT_CLOUD,
    PT_SUBSAMPLE_THRESHOLD, PT_SUBSAMPLE_TARGET,
    PT_CLOUD_SIZE_DEFAULT, POINT_FOG, POINT_FOG_START,
    PT_CLOUD_SHADER_SCALE,
    PT_CLOUD_SHADER_SIZE_MIN, PT_CLOUD_SHADER_SIZE_MAX,

    STARTUP_AUDIO_MODE,
    AUDIO_ISO_AXIS, AUDIO_COLOR_AXIS, AUDIO_ISO_COUNT_DEFAULT,
    AUDIO_TARGET_FPS, AUDIO_FREQ_SAMPLES, AUDIO_TIME_RANGE,
    AUDIO_FOCUS_FREQ_RANGE,
    AUDIO_QUIET_THRESHOLD, AUDIO_MIN_DB_THRESHOLD,
    AUDIO_CAM_POSITION, AUDIO_CAM_FOCAL_POINT,
)

logger = logging.getLogger(__name__)

_SETTINGS_LOG_FILENAME = 'settings.log'

def write_settings_log(
    save_dir: str,
    geo_type: str = 'mesh',
    input_path: str = '',
) -> None:
    os.makedirs(save_dir, exist_ok=True)
    log_path = os.path.join(save_dir, _SETTINGS_LOG_FILENAME)
    ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    lines = [
        f'# MeshViewer Settings Log ({ts})',
        f'# input={input_path}',
        f'# geo_type={geo_type}',
        '',
        '# Window',
        f'WINDOW_WIDTH={WINDOW_WIDTH}',
        f'WINDOW_HEIGHT={WINDOW_HEIGHT}',
        f'WINDOW_ASPECT_RATIO={WINDOW_ASPECT_RATIO}',
        '',
        '# Render Quality',
        f'RENDER_MSAA_SAMPLES={RENDER_MSAA_SAMPLES}',
        f'RENDER_FXAA={RENDER_FXAA}',
        f'RENDER_LINE_SMOOTHING={RENDER_LINE_SMOOTHING}',
        f'RENDER_POINT_SMOOTHING={RENDER_POINT_SMOOTHING}',
        f'SAVE_ALPHA={SAVE_ALPHA}',
        '',
        '# Animation',
        f'TARGET_ANIM_FPS={TARGET_ANIM_FPS}',
        f'DEFAULT_ANIMATION={DEFAULT_ANIMATION}',
        f'DEFAULT_TURNTABLE={DEFAULT_TURNTABLE}',
        f'TURNTABLE_STEP={TURNTABLE_STEP}',
        f'MAX_FRAME_SKIP={MAX_FRAME_SKIP}',
        '',
        '# Startup Camera',
        f'STARTUP_AXIS={STARTUP_AXIS}',
        f'STARTUP_REVERSE_X_AXIS={STARTUP_REVERSE_X_AXIS}',
        f'STARTUP_REVERSE_Y_AXIS={STARTUP_REVERSE_Y_AXIS}',
        f'STARTUP_REVERSE_Z_AXIS={STARTUP_REVERSE_Z_AXIS}',
        f'FLIP_OBJECT_X={FLIP_OBJECT_X}',
        f'FLIP_OBJECT_Y={FLIP_OBJECT_Y}',
        f'FLIP_OBJECT_Z={FLIP_OBJECT_Z}',
        f'CAM_DIST_FACTOR={CAM_DIST_FACTOR}',
        f'STARTUP_CAM_DEGREE={STARTUP_CAM_DEGREE}',
        f'STARTUP_CAM_POSITION={STARTUP_CAM_POSITION}',
        f'STARTUP_FOCAL_LENGTH={STARTUP_FOCAL_LENGTH}',
        f'STARTUP_ZOOM={STARTUP_ZOOM}',
        '',
        '# Default View',
        f'DEFAULT_GRID={DEFAULT_GRID}',
        f'DEFAULT_BBOX={DEFAULT_BBOX}',
        f'DEFAULT_BACKFACE={DEFAULT_BACKFACE}',
        f'DEFAULT_LIGHTING={DEFAULT_LIGHTING}',
        '',
        '# Save',
        f'SAVE_FILENAME_EXT={SAVE_FILENAME_EXT}',
        f'SAVE_PBO_ENABLED={SAVE_PBO_ENABLED}',
        '',
        '# System',
        f'WORKER_COUNT={WORKER_COUNT}',
    ]
    lines += _build_mode_lines(geo_type)
    with open(log_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines) + '\n')
    logger.info('Settings log written: %s', log_path)

def _build_mode_lines(geo_type: str) -> list:
    if geo_type == 'mesh':
        return [
            '',
            '# Mesh',
            f'STARTUP_MODE={STARTUP_MODE}',
            f'DEFAULT_TEXTURE={DEFAULT_TEXTURE}',
            f'DEFAULT_SMOOTH={DEFAULT_SMOOTH}',
            f'HDRI_ENABLE={HDRI_ENABLE}',
            f'PBR_METALLIC={PBR_METALLIC}',
            f'PBR_ROUGHNESS={PBR_ROUGHNESS}',
            f'REDUCTION_MESH={REDUCTION_MESH}',
            f'AUTO_DECIMATE_THRESHOLD={AUTO_DECIMATE_THRESHOLD}',
            f'AUTO_DECIMATE_MAX_CELLS={AUTO_DECIMATE_MAX_CELLS}',
            f'ISOLINE_CONTOUR_MAX_FACES={ISOLINE_CONTOUR_MAX_FACES}',
            f'ISO_COUNT_DEFAULT={ISO_COUNT_DEFAULT}',
            f'COLOR_ISO_LINE={COLOR_ISO_LINE}',
            f'WIDTH_ISO_LINE={WIDTH_ISO_LINE}',
            f'COLOR_WIREFRAME={COLOR_WIREFRAME}',
            f'WIDTH_WIREFRAME={WIDTH_WIREFRAME}',
            f'EDGE_FEATURE_ANGLE={EDGE_FEATURE_ANGLE}',
            f'DEPTH_AXIS_DEFAULT={DEPTH_AXIS_DEFAULT}',
            f'MESH_QUALITY_METRIC={MESH_QUALITY_METRIC}',
        ]
    if geo_type == 'point_cloud':
        return [
            '',
            '# Point Cloud',
            f'STARTUP_MODE_POINT_CLOUD={STARTUP_MODE_POINT_CLOUD}',
            f'PT_SUBSAMPLE_THRESHOLD={PT_SUBSAMPLE_THRESHOLD}',
            f'PT_SUBSAMPLE_TARGET={PT_SUBSAMPLE_TARGET}',
            f'PT_CLOUD_SIZE_DEFAULT={PT_CLOUD_SIZE_DEFAULT}',
            f'POINT_FOG={POINT_FOG}',
            f'POINT_FOG_START={POINT_FOG_START}',
            f'PT_CLOUD_SHADER_SCALE={PT_CLOUD_SHADER_SCALE}',
            f'PT_CLOUD_SHADER_SIZE_MIN={PT_CLOUD_SHADER_SIZE_MIN}',
            f'PT_CLOUD_SHADER_SIZE_MAX={PT_CLOUD_SHADER_SIZE_MAX}',
        ]
    if geo_type == 'audio':
        return [
            '',
            '# Audio',
            f'STARTUP_AUDIO_MODE={STARTUP_AUDIO_MODE}',
            f'AUDIO_ISO_AXIS={AUDIO_ISO_AXIS}',
            f'AUDIO_COLOR_AXIS={AUDIO_COLOR_AXIS}',
            f'AUDIO_ISO_COUNT_DEFAULT={AUDIO_ISO_COUNT_DEFAULT}',
            f'AUDIO_TARGET_FPS={AUDIO_TARGET_FPS}',
            f'AUDIO_FREQ_SAMPLES={AUDIO_FREQ_SAMPLES}',
            f'AUDIO_TIME_RANGE={AUDIO_TIME_RANGE}',
            f'AUDIO_FOCUS_FREQ_RANGE={AUDIO_FOCUS_FREQ_RANGE}',
            f'AUDIO_QUIET_THRESHOLD={AUDIO_QUIET_THRESHOLD}',
            f'AUDIO_MIN_DB_THRESHOLD={AUDIO_MIN_DB_THRESHOLD}',
            f'AUDIO_CAM_POSITION={AUDIO_CAM_POSITION}',
            f'AUDIO_CAM_FOCAL_POINT={AUDIO_CAM_FOCAL_POINT}',
        ]
    return []

def log_session_start(obj_files: list, args) -> None:

    ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
    level = 'DEBUG' if getattr(args, 'verbose', False) else 'INFO'
    log_msg = (
        f'MeshViewer Session Start - Input: "{args.input}", '
        f'Files: {len(obj_files)}, '
        f'Start Time: {ts}, '
        f'Window: {WINDOW_WIDTH}x{WINDOW_HEIGHT}, '
        f'fps: {TARGET_ANIM_FPS}, '
        f'Log Level: {level}'
    )
    if args.save:
        log_msg += f', Save Path: "{args.save}"'
    logger.info(log_msg)

    _rev_axes = [
        ax for ax, flag in (
            ('X', STARTUP_REVERSE_X_AXIS),
            ('Y', STARTUP_REVERSE_Y_AXIS),
            ('Z', STARTUP_REVERSE_Z_AXIS),
        ) if flag
    ]
    _flip_axes = [
        ax for ax, flag in (
            ('X', FLIP_OBJECT_X),
            ('Y', FLIP_OBJECT_Y),
            ('Z', FLIP_OBJECT_Z),
        ) if flag
    ]
    logger.info(
        'Startup Axis: AXIS_SWAP=%s, REVERSE=%s, FLIP_OBJECT=%s',
        STARTUP_AXIS,
        _rev_axes if _rev_axes else 'none',
        _flip_axes if _flip_axes else 'none',
    )

def log_session_end(
    input_name: str,
    total: int,
    start_t: float | None = None,
    save_counter: int = 0,
    save_path: str | None = None,
) -> None:
    import time
    if start_t:
        delta = time.time() - start_t
        h = int(delta // 3600)
        m = int((delta % 3600) // 60)
        s = delta % 60
        elapsed = f'{h:02d}:{m:02d}:{s:06.3f}'
    else:
        elapsed = '?'
    log_msg = (
        f'MeshViewer Session End - Input: "{input_name}", '
        f'Total: {total} frames, Elapsed Time: {elapsed}'
    )
    if save_path and save_counter > 0:
        log_msg += f', Saved: {save_counter} frames. ({save_path})'
    logger.info(log_msg)
