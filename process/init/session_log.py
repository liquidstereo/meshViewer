import os
import logging
from datetime import datetime

from configs.settings import (
    WINDOW_WIDTH, WINDOW_HEIGHT, WINDOW_ASPECT_RATIO,
    TARGET_ANIM_FPS, SHOW_ANIMATION,
    SHOW_TURNTABLE, TURNTABLE_STEP, MAX_FRAME_SKIP,
    RENDER_MSAA_SAMPLES, RENDER_FXAA,
    RENDER_LINE_SMOOTHING, RENDER_POINT_SMOOTHING,
    SAVE_ALPHA, SAVE_PNG_COMPRESSION, SAVE_JPEG_QUALITY,
    SAVE_FILENAME_EXT, SAVE_PBO_ENABLED,
    STARTUP_AXIS,
    STARTUP_REVERSE_X_AXIS, STARTUP_REVERSE_Y_AXIS, STARTUP_REVERSE_Z_AXIS,
    FLIP_OBJECT_X, FLIP_OBJECT_Y, FLIP_OBJECT_Z,
    CAM_DIST_FACTOR, STARTUP_CAM_DEGREE,
    STARTUP_CAM_POSITION, STARTUP_FOCAL_LENGTH, STARTUP_ZOOM,
    SHOW_GRID, SHOW_BBOX, SHOW_BACKFACE, SHOW_LIGHTING,
    SHOW_HIDE_INFO, SHOW_COLORBAR, SHOW_IMAGE_SEQUENCE, SHOW_MESH,
    MESH_MATTE_COLOR, COLOR_BG,
    WORKER_COUNT,
    resolve_axis_settings,

    STARTUP_MODE, DEFAULT_TEXTURE, DEFAULT_SMOOTH,
    HDRI_PATH, HDRI_ENABLE, HDRI_INTENSITY, HDRI_ROT_STEP,
    PBR_METALLIC, PBR_ROUGHNESS, PBR_ANISOTROPY,
    COLOR_MESH_DEFAULT, COLOR_MESH_ISO, COLOR_MESH_NO_TEX,
    REDUCTION_MESH, REDUCTION_MESH_STEP, REDUCTION_MESH_QUALITY,
    AUTO_DECIMATE_THRESHOLD, AUTO_DECIMATE_MAX_CELLS, AUTO_DECIMATE_MAX_RATIO,
    ISOLINE_CONTOUR_MAX_FACES,
    ISO_COUNT_DEFAULT, ISO_COUNT_STEP, COLOR_ISO_LINE, WIDTH_ISO_LINE,
    TYPE_TUBE, ISO_NORMAL_OFFSET,
    COLOR_WIREFRAME, WIDTH_WIREFRAME,
    COLOR_EDGE, WIDTH_EDGE,
    EDGE_FEATURE_ANGLE, EDGE_FEATURE_ANGLE_STEP,
    MESH_DEPTH_COLOR, DEPTH_AXIS_DEFAULT, DEPTH_SHADING_FLAT,
    DEPTH_ENABLE_LIGHTING,
    NORMAL_COLOR_ENABLE_LIGHTING,
    FNORMAL_SPATIAL_INTERVAL, FNORMAL_CMAP, FNORMAL_MESH_OPACITY, FNORMAL_SCALE,
    COLOR_MESH_QUALITY, MESH_QUALITY_METRIC,
    VTX_SPATIAL_INTERVAL, VTX_SPATIAL_STEP, VTX_SCREEN_INTERVAL, VTX_POINT_SIZE,
    MESH_STARTUP_AXIS,
    MESH_STARTUP_REVERSE_X_AXIS, MESH_STARTUP_REVERSE_Y_AXIS,
    MESH_STARTUP_REVERSE_Z_AXIS,
    MESH_FLIP_OBJECT_X, MESH_FLIP_OBJECT_Y, MESH_FLIP_OBJECT_Z,

    STARTUP_MODE_POINT_CLOUD, POINTS_COLOR,
    PT_SUBSAMPLE_THRESHOLD, PT_SUBSAMPLE_TARGET,
    PT_CLOUD_DEPTH_COLOR, PT_CLOUD_DEPTH_CONTRAST,
    POINT_FOG, POINT_FOG_START,
    PT_CLOUD_SIZE_DEFAULT, PT_CLOUD_SIZE_POINT_WHITE, PT_CLOUD_SIZE_DEPTH,
    PT_CLOUD_SIZE_STEP, PT_CLOUD_SIZE_MIN, PT_CLOUD_SIZE_MAX,
    PT_CLOUD_SHADER_SCALE, PT_CLOUD_SHADER_SIZE_MIN, PT_CLOUD_SHADER_SIZE_MAX,
    PT_STARTUP_AXIS,
    PT_STARTUP_REVERSE_X_AXIS, PT_STARTUP_REVERSE_Y_AXIS,
    PT_STARTUP_REVERSE_Z_AXIS,
    PT_FLIP_OBJECT_X, PT_FLIP_OBJECT_Y, PT_FLIP_OBJECT_Z,

    NPY_AS_POINTCLOUD,
    DATA_NORMALIZE, DATA_NORMALIZE_VALUE,
    DATA_NORMALIZE_AXIS, DATA_NORMALIZE_LOG,
    NP_STARTUP_MODE_POINT_CLOUD, NP_POINTS_COLOR,
    NP_SUBSAMPLE_THRESHOLD, NP_SUBSAMPLE_TARGET,
    NP_CLOUD_DEPTH_COLOR, NP_CLOUD_DEPTH_CONTRAST,
    NP_POINT_FOG, NP_POINT_FOG_START,
    NP_CLOUD_SIZE_DEFAULT, NP_CLOUD_SIZE_POINT_WHITE, NP_CLOUD_SIZE_DEPTH,
    NP_CLOUD_SIZE_STEP, NP_CLOUD_SIZE_MIN, NP_CLOUD_SIZE_MAX,
    NP_CLOUD_SHADER_SCALE, NP_CLOUD_SHADER_SIZE_MIN, NP_CLOUD_SHADER_SIZE_MAX,
    NP_STARTUP_AXIS,
    NP_STARTUP_REVERSE_X_AXIS, NP_STARTUP_REVERSE_Y_AXIS,
    NP_STARTUP_REVERSE_Z_AXIS,
    NP_FLIP_OBJECT_X, NP_FLIP_OBJECT_Y, NP_FLIP_OBJECT_Z,

    STARTUP_AUDIO_MODE,
    AUDIO_ISO_AXIS, AUDIO_COLOR_AXIS, AUDIO_ISO_COUNT_DEFAULT,
    AUDIO_ISOLINE_CMAP, AUDIO_WIREFRAME_CMAP, AUDIO_MESH_CMAP,
    AUDIO_DEPTH_CMAP, AUDIO_EDGE_CMAP, AUDIO_QUALITY_CMAP, AUDIO_FNORMAL_CMAP,
    AUDIO_TARGET_FPS, AUDIO_FREQ_SAMPLES, AUDIO_TIME_RANGE,
    AUDIO_FOCUS_FREQ_RANGE, AUDIO_REFERENCE_FRAMES,
    AUDIO_QUIET_THRESHOLD, AUDIO_MIN_DB_THRESHOLD, AUDIO_MIN_MESH_VALUE,
    AUDIO_GRID_Y_MAX, AUDIO_FREQ_NORM_MAX,
    AUDIO_FADE_WIDTH, AUDIO_MESH_SMOOTHING_ITERS,
    AUDIO_MESH_Y_OFFSET, AUDIO_MESH_Y_CUTOFF,
    AUDIO_ISOLINE_WIDTH, AUDIO_ISO_OFFSET, AUDIO_WIREFRAME_LINE_WIDTH,
    AUDIO_EDGE_FEATURE_ANGLE,
    AUDIO_FNORMAL_SPATIAL_INTERVAL, AUDIO_FNORMAL_SCALE,
    AUDIO_SEEK_STEP,
    AUDIO_CAM_POSITION, AUDIO_CAM_FOCAL_POINT, AUDIO_CAM_UP,
    AUDIO_STARTUP_AXIS,
    AUDIO_STARTUP_REVERSE_X_AXIS, AUDIO_STARTUP_REVERSE_Y_AXIS,
    AUDIO_STARTUP_REVERSE_Z_AXIS,
    AUDIO_FLIP_OBJECT_X, AUDIO_FLIP_OBJECT_Y, AUDIO_FLIP_OBJECT_Z,
)

logger = logging.getLogger(__name__)

_SETTINGS_LOG_FILENAME = 'settings.log'
_NP_DATA_EXTS = ('.npy', '.npz')

def write_settings_log(
    save_dir: str,
    geo_type: str = 'mesh',
    input_path: str = '',
) -> None:
    os.makedirs(save_dir, exist_ok=True)
    log_path = os.path.join(save_dir, _SETTINGS_LOG_FILENAME)
    ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    (
        _axis, _rx, _ry, _rz, _fx, _fy, _fz,
    ) = resolve_axis_settings(geo_type)
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
        f'SAVE_PNG_COMPRESSION={SAVE_PNG_COMPRESSION}',
        f'SAVE_JPEG_QUALITY={SAVE_JPEG_QUALITY}',
        '',
        '# Animation',
        f'TARGET_ANIM_FPS={TARGET_ANIM_FPS}',
        f'SHOW_ANIMATION={SHOW_ANIMATION}',
        f'SHOW_TURNTABLE={SHOW_TURNTABLE}',
        f'TURNTABLE_STEP={TURNTABLE_STEP}',
        f'MAX_FRAME_SKIP={MAX_FRAME_SKIP}',
        '',
        '# Startup Camera (resolved for geo_type)',
        f'STARTUP_AXIS={_axis}',
        f'STARTUP_REVERSE_X_AXIS={_rx}',
        f'STARTUP_REVERSE_Y_AXIS={_ry}',
        f'STARTUP_REVERSE_Z_AXIS={_rz}',
        f'FLIP_OBJECT_X={_fx}',
        f'FLIP_OBJECT_Y={_fy}',
        f'FLIP_OBJECT_Z={_fz}',
        f'CAM_DIST_FACTOR={CAM_DIST_FACTOR}',
        f'STARTUP_CAM_DEGREE={STARTUP_CAM_DEGREE}',
        f'STARTUP_CAM_POSITION={STARTUP_CAM_POSITION}',
        f'STARTUP_FOCAL_LENGTH={STARTUP_FOCAL_LENGTH}',
        f'STARTUP_ZOOM={STARTUP_ZOOM}',
        '',
        '# Default View',
        f'SHOW_GRID={SHOW_GRID}',
        f'SHOW_BBOX={SHOW_BBOX}',
        f'SHOW_BACKFACE={SHOW_BACKFACE}',
        f'SHOW_LIGHTING={SHOW_LIGHTING}',
        f'SHOW_HIDE_INFO={SHOW_HIDE_INFO}',
        f'SHOW_COLORBAR={SHOW_COLORBAR}',
        f'SHOW_IMAGE_SEQUENCE={SHOW_IMAGE_SEQUENCE}',
        f'SHOW_MESH={SHOW_MESH}',
        f'MESH_MATTE_COLOR={MESH_MATTE_COLOR}',
        f'COLOR_BG={COLOR_BG}',
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
            f'HDRI_PATH={HDRI_PATH}',
            f'HDRI_ENABLE={HDRI_ENABLE}',
            f'HDRI_INTENSITY={HDRI_INTENSITY}',
            f'HDRI_ROT_STEP={HDRI_ROT_STEP}',
            f'PBR_METALLIC={PBR_METALLIC}',
            f'PBR_ROUGHNESS={PBR_ROUGHNESS}',
            f'PBR_ANISOTROPY={PBR_ANISOTROPY}',
            f'COLOR_MESH_DEFAULT={COLOR_MESH_DEFAULT}',
            f'COLOR_MESH_ISO={COLOR_MESH_ISO}',
            f'COLOR_MESH_NO_TEX={COLOR_MESH_NO_TEX}',
            '',
            '# Mesh Reduction',
            f'REDUCTION_MESH={REDUCTION_MESH}',
            f'REDUCTION_MESH_STEP={REDUCTION_MESH_STEP}',
            f'REDUCTION_MESH_QUALITY={REDUCTION_MESH_QUALITY}',
            f'AUTO_DECIMATE_THRESHOLD={AUTO_DECIMATE_THRESHOLD}',
            f'AUTO_DECIMATE_MAX_CELLS={AUTO_DECIMATE_MAX_CELLS}',
            f'AUTO_DECIMATE_MAX_RATIO={AUTO_DECIMATE_MAX_RATIO}',
            f'ISOLINE_CONTOUR_MAX_FACES={ISOLINE_CONTOUR_MAX_FACES}',
            '',
            '# Isoline',
            f'ISO_COUNT_DEFAULT={ISO_COUNT_DEFAULT}',
            f'ISO_COUNT_STEP={ISO_COUNT_STEP}',
            f'COLOR_ISO_LINE={COLOR_ISO_LINE}',
            f'WIDTH_ISO_LINE={WIDTH_ISO_LINE}',
            f'TYPE_TUBE={TYPE_TUBE}',
            f'ISO_NORMAL_OFFSET={ISO_NORMAL_OFFSET}',
            '',
            '# Wireframe',
            f'COLOR_WIREFRAME={COLOR_WIREFRAME}',
            f'WIDTH_WIREFRAME={WIDTH_WIREFRAME}',
            '',
            '# Edge',
            f'COLOR_EDGE={COLOR_EDGE}',
            f'WIDTH_EDGE={WIDTH_EDGE}',
            f'EDGE_FEATURE_ANGLE={EDGE_FEATURE_ANGLE}',
            f'EDGE_FEATURE_ANGLE_STEP={EDGE_FEATURE_ANGLE_STEP}',
            '',
            '# Depth',
            f'MESH_DEPTH_COLOR={MESH_DEPTH_COLOR}',
            f'DEPTH_AXIS_DEFAULT={DEPTH_AXIS_DEFAULT}',
            f'DEPTH_SHADING_FLAT={DEPTH_SHADING_FLAT}',
            f'DEPTH_ENABLE_LIGHTING={DEPTH_ENABLE_LIGHTING}',
            '',
            '# Normal / Face Normal',
            f'NORMAL_COLOR_ENABLE_LIGHTING={NORMAL_COLOR_ENABLE_LIGHTING}',
            f'FNORMAL_SPATIAL_INTERVAL={FNORMAL_SPATIAL_INTERVAL}',
            f'FNORMAL_CMAP={FNORMAL_CMAP}',
            f'FNORMAL_MESH_OPACITY={FNORMAL_MESH_OPACITY}',
            f'FNORMAL_SCALE={FNORMAL_SCALE}',
            '',
            '# Mesh Quality',
            f'COLOR_MESH_QUALITY={COLOR_MESH_QUALITY}',
            f'MESH_QUALITY_METRIC={MESH_QUALITY_METRIC}',
            '',
            '# Vertex Label',
            f'VTX_SPATIAL_INTERVAL={VTX_SPATIAL_INTERVAL}',
            f'VTX_SPATIAL_STEP={VTX_SPATIAL_STEP}',
            f'VTX_SCREEN_INTERVAL={VTX_SCREEN_INTERVAL}',
            f'VTX_POINT_SIZE={VTX_POINT_SIZE}',
            '',
            '# Axis Override (mesh)',
            f'MESH_STARTUP_AXIS={MESH_STARTUP_AXIS}',
            f'MESH_STARTUP_REVERSE_X_AXIS={MESH_STARTUP_REVERSE_X_AXIS}',
            f'MESH_STARTUP_REVERSE_Y_AXIS={MESH_STARTUP_REVERSE_Y_AXIS}',
            f'MESH_STARTUP_REVERSE_Z_AXIS={MESH_STARTUP_REVERSE_Z_AXIS}',
            f'MESH_FLIP_OBJECT_X={MESH_FLIP_OBJECT_X}',
            f'MESH_FLIP_OBJECT_Y={MESH_FLIP_OBJECT_Y}',
            f'MESH_FLIP_OBJECT_Z={MESH_FLIP_OBJECT_Z}',
        ]
    if geo_type == 'point_cloud':
        return [
            '',
            '# Point Cloud',
            f'STARTUP_MODE_POINT_CLOUD={STARTUP_MODE_POINT_CLOUD}',
            f'POINTS_COLOR={POINTS_COLOR}',
            f'PT_SUBSAMPLE_THRESHOLD={PT_SUBSAMPLE_THRESHOLD}',
            f'PT_SUBSAMPLE_TARGET={PT_SUBSAMPLE_TARGET}',
            '',
            '# Point Cloud Depth',
            f'PT_CLOUD_DEPTH_COLOR={PT_CLOUD_DEPTH_COLOR}',
            f'PT_CLOUD_DEPTH_CONTRAST={PT_CLOUD_DEPTH_CONTRAST}',
            f'POINT_FOG={POINT_FOG}',
            f'POINT_FOG_START={POINT_FOG_START}',
            '',
            '# Point Cloud Size',
            f'PT_CLOUD_SIZE_DEFAULT={PT_CLOUD_SIZE_DEFAULT}',
            f'PT_CLOUD_SIZE_POINT_WHITE={PT_CLOUD_SIZE_POINT_WHITE}',
            f'PT_CLOUD_SIZE_DEPTH={PT_CLOUD_SIZE_DEPTH}',
            f'PT_CLOUD_SIZE_STEP={PT_CLOUD_SIZE_STEP}',
            f'PT_CLOUD_SIZE_MIN={PT_CLOUD_SIZE_MIN}',
            f'PT_CLOUD_SIZE_MAX={PT_CLOUD_SIZE_MAX}',
            '',
            '# Point Cloud Shader',
            f'PT_CLOUD_SHADER_SCALE={PT_CLOUD_SHADER_SCALE}',
            f'PT_CLOUD_SHADER_SIZE_MIN={PT_CLOUD_SHADER_SIZE_MIN}',
            f'PT_CLOUD_SHADER_SIZE_MAX={PT_CLOUD_SHADER_SIZE_MAX}',
            '',
            '# Axis Override (point_cloud)',
            f'PT_STARTUP_AXIS={PT_STARTUP_AXIS}',
            f'PT_STARTUP_REVERSE_X_AXIS={PT_STARTUP_REVERSE_X_AXIS}',
            f'PT_STARTUP_REVERSE_Y_AXIS={PT_STARTUP_REVERSE_Y_AXIS}',
            f'PT_STARTUP_REVERSE_Z_AXIS={PT_STARTUP_REVERSE_Z_AXIS}',
            f'PT_FLIP_OBJECT_X={PT_FLIP_OBJECT_X}',
            f'PT_FLIP_OBJECT_Y={PT_FLIP_OBJECT_Y}',
            f'PT_FLIP_OBJECT_Z={PT_FLIP_OBJECT_Z}',
        ]
    if geo_type == 'np_data':
        return [
            '',
            '# NPY/NPZ Preprocessing',
            f'NPY_AS_POINTCLOUD={NPY_AS_POINTCLOUD}',
            f'DATA_NORMALIZE={DATA_NORMALIZE}',
            f'DATA_NORMALIZE_VALUE={DATA_NORMALIZE_VALUE}',
            f'DATA_NORMALIZE_AXIS={DATA_NORMALIZE_AXIS}',
            f'DATA_NORMALIZE_LOG={DATA_NORMALIZE_LOG}',
            '',
            '# NP Data Point Cloud',
            f'NP_STARTUP_MODE_POINT_CLOUD={NP_STARTUP_MODE_POINT_CLOUD}',
            f'NP_POINTS_COLOR={NP_POINTS_COLOR}',
            f'NP_SUBSAMPLE_THRESHOLD={NP_SUBSAMPLE_THRESHOLD}',
            f'NP_SUBSAMPLE_TARGET={NP_SUBSAMPLE_TARGET}',
            '',
            '# NP Data Depth',
            f'NP_CLOUD_DEPTH_COLOR={NP_CLOUD_DEPTH_COLOR}',
            f'NP_CLOUD_DEPTH_CONTRAST={NP_CLOUD_DEPTH_CONTRAST}',
            f'NP_POINT_FOG={NP_POINT_FOG}',
            f'NP_POINT_FOG_START={NP_POINT_FOG_START}',
            '',
            '# NP Data Point Size',
            f'NP_CLOUD_SIZE_DEFAULT={NP_CLOUD_SIZE_DEFAULT}',
            f'NP_CLOUD_SIZE_POINT_WHITE={NP_CLOUD_SIZE_POINT_WHITE}',
            f'NP_CLOUD_SIZE_DEPTH={NP_CLOUD_SIZE_DEPTH}',
            f'NP_CLOUD_SIZE_STEP={NP_CLOUD_SIZE_STEP}',
            f'NP_CLOUD_SIZE_MIN={NP_CLOUD_SIZE_MIN}',
            f'NP_CLOUD_SIZE_MAX={NP_CLOUD_SIZE_MAX}',
            '',
            '# NP Data Shader',
            f'NP_CLOUD_SHADER_SCALE={NP_CLOUD_SHADER_SCALE}',
            f'NP_CLOUD_SHADER_SIZE_MIN={NP_CLOUD_SHADER_SIZE_MIN}',
            f'NP_CLOUD_SHADER_SIZE_MAX={NP_CLOUD_SHADER_SIZE_MAX}',
            '',
            '# Axis Override (np_data)',
            f'NP_STARTUP_AXIS={NP_STARTUP_AXIS}',
            f'NP_STARTUP_REVERSE_X_AXIS={NP_STARTUP_REVERSE_X_AXIS}',
            f'NP_STARTUP_REVERSE_Y_AXIS={NP_STARTUP_REVERSE_Y_AXIS}',
            f'NP_STARTUP_REVERSE_Z_AXIS={NP_STARTUP_REVERSE_Z_AXIS}',
            f'NP_FLIP_OBJECT_X={NP_FLIP_OBJECT_X}',
            f'NP_FLIP_OBJECT_Y={NP_FLIP_OBJECT_Y}',
            f'NP_FLIP_OBJECT_Z={NP_FLIP_OBJECT_Z}',
        ]
    if geo_type == 'audio':
        return [
            '',
            '# Audio Mode',
            f'STARTUP_AUDIO_MODE={STARTUP_AUDIO_MODE}',
            f'AUDIO_ISO_AXIS={AUDIO_ISO_AXIS}',
            f'AUDIO_COLOR_AXIS={AUDIO_COLOR_AXIS}',
            f'AUDIO_ISO_COUNT_DEFAULT={AUDIO_ISO_COUNT_DEFAULT}',
            '',
            '# Audio Colormap',
            f'AUDIO_ISOLINE_CMAP={AUDIO_ISOLINE_CMAP}',
            f'AUDIO_WIREFRAME_CMAP={AUDIO_WIREFRAME_CMAP}',
            f'AUDIO_MESH_CMAP={AUDIO_MESH_CMAP}',
            f'AUDIO_DEPTH_CMAP={AUDIO_DEPTH_CMAP}',
            f'AUDIO_EDGE_CMAP={AUDIO_EDGE_CMAP}',
            f'AUDIO_QUALITY_CMAP={AUDIO_QUALITY_CMAP}',
            f'AUDIO_FNORMAL_CMAP={AUDIO_FNORMAL_CMAP}',
            '',
            '# Audio Processing',
            f'AUDIO_TARGET_FPS={AUDIO_TARGET_FPS}',
            f'AUDIO_FREQ_SAMPLES={AUDIO_FREQ_SAMPLES}',
            f'AUDIO_TIME_RANGE={AUDIO_TIME_RANGE}',
            f'AUDIO_FOCUS_FREQ_RANGE={AUDIO_FOCUS_FREQ_RANGE}',
            f'AUDIO_REFERENCE_FRAMES={AUDIO_REFERENCE_FRAMES}',
            f'AUDIO_QUIET_THRESHOLD={AUDIO_QUIET_THRESHOLD}',
            f'AUDIO_MIN_DB_THRESHOLD={AUDIO_MIN_DB_THRESHOLD}',
            f'AUDIO_MIN_MESH_VALUE={AUDIO_MIN_MESH_VALUE}',
            f'AUDIO_GRID_Y_MAX={AUDIO_GRID_Y_MAX}',
            f'AUDIO_FREQ_NORM_MAX={AUDIO_FREQ_NORM_MAX}',
            '',
            '# Audio Geometry',
            f'AUDIO_FADE_WIDTH={AUDIO_FADE_WIDTH}',
            f'AUDIO_MESH_SMOOTHING_ITERS={AUDIO_MESH_SMOOTHING_ITERS}',
            f'AUDIO_MESH_Y_OFFSET={AUDIO_MESH_Y_OFFSET}',
            f'AUDIO_MESH_Y_CUTOFF={AUDIO_MESH_Y_CUTOFF}',
            '',
            '# Audio Style',
            f'AUDIO_ISOLINE_WIDTH={AUDIO_ISOLINE_WIDTH}',
            f'AUDIO_ISO_OFFSET={AUDIO_ISO_OFFSET}',
            f'AUDIO_WIREFRAME_LINE_WIDTH={AUDIO_WIREFRAME_LINE_WIDTH}',
            f'AUDIO_EDGE_FEATURE_ANGLE={AUDIO_EDGE_FEATURE_ANGLE}',
            f'AUDIO_FNORMAL_SPATIAL_INTERVAL={AUDIO_FNORMAL_SPATIAL_INTERVAL}',
            f'AUDIO_FNORMAL_SCALE={AUDIO_FNORMAL_SCALE}',
            f'AUDIO_SEEK_STEP={AUDIO_SEEK_STEP}',
            '',
            '# Audio Camera',
            f'AUDIO_CAM_POSITION={AUDIO_CAM_POSITION}',
            f'AUDIO_CAM_FOCAL_POINT={AUDIO_CAM_FOCAL_POINT}',
            f'AUDIO_CAM_UP={AUDIO_CAM_UP}',
            '',
            '# Axis Override (audio)',
            f'AUDIO_STARTUP_AXIS={AUDIO_STARTUP_AXIS}',
            f'AUDIO_STARTUP_REVERSE_X_AXIS={AUDIO_STARTUP_REVERSE_X_AXIS}',
            f'AUDIO_STARTUP_REVERSE_Y_AXIS={AUDIO_STARTUP_REVERSE_Y_AXIS}',
            f'AUDIO_STARTUP_REVERSE_Z_AXIS={AUDIO_STARTUP_REVERSE_Z_AXIS}',
            f'AUDIO_FLIP_OBJECT_X={AUDIO_FLIP_OBJECT_X}',
            f'AUDIO_FLIP_OBJECT_Y={AUDIO_FLIP_OBJECT_Y}',
            f'AUDIO_FLIP_OBJECT_Z={AUDIO_FLIP_OBJECT_Z}',
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

    _ext = (
        os.path.splitext(obj_files[0])[1].lower() if obj_files else ''
    )
    _ftype = (
        'np_data' if _ext in _NP_DATA_EXTS
        else getattr(args, '_file_type', 'mesh')
    )
    (
        _axis, _rx, _ry, _rz, _fx, _fy, _fz,
    ) = resolve_axis_settings(_ftype)
    _rev_axes = [
        ax for ax, flag in (('X', _rx), ('Y', _ry), ('Z', _rz)) if flag
    ]
    _flip_axes = [
        ax for ax, flag in (('X', _fx), ('Y', _fy), ('Z', _fz)) if flag
    ]
    logger.info(
        'Startup Axis [%s]: AXIS_SWAP=%s, REVERSE=%s, FLIP_OBJECT=%s',
        _ftype,
        _axis,
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
