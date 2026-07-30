import os
import shutil
import logging
import subprocess

import numpy as np

from configs.settings import (
    FFMPEG_BIN, SAVE_VIDEO_CODEC, SAVE_VIDEO_FASTSTART,
    SAVE_VIDEO_LOG_LEVEL, SAVE_VIDEO_EXTS, SAVE_IMAGE_EXTS,
    SAVE_QUALITY, SAVE_QUALITY_PRESETS, AVOID_NAME_COLLISION,
)

logger = logging.getLogger(__name__)

_EVEN_FILTER = 'scale=trunc(iw/2)*2:trunc(ih/2)*2'

_NO_SUBSAMPLE_FMTS = ('yuv444p', 'yuv444p10le', 'rgb24')

def resolve_quality(name: str) -> dict:
    preset = SAVE_QUALITY_PRESETS.get(name)
    if preset is None:
        logger.warning(
            'Unknown quality %r - falling back to %r', name, SAVE_QUALITY,
        )
        preset = SAVE_QUALITY_PRESETS[SAVE_QUALITY]
    return preset

def is_video_ext(ext: str) -> bool:
    return ext.lower().lstrip('.') in SAVE_VIDEO_EXTS

def is_image_ext(ext: str) -> bool:
    return ext.lower().lstrip('.') in SAVE_IMAGE_EXTS

def resolve_output_path(out_dir: str, stem: str, ext: str) -> str:
    path = os.path.join(out_dir, f'{stem}.{ext}')
    if not AVOID_NAME_COLLISION or not os.path.exists(path):
        return path
    idx = 1
    while os.path.exists(path):
        path = os.path.join(out_dir, f'{stem}_{idx:02d}.{ext}')
        idx += 1
    return path

def build_ffmpeg_command(path: str, width: int, height: int,
                         fps: int, n_comp: int,
                         quality: str = SAVE_QUALITY) -> list:
    cfg = resolve_quality(quality)
    pix_fmt = cfg['pix_fmt']
    codec = cfg.get('codec', SAVE_VIDEO_CODEC)
    cmd = [
        FFMPEG_BIN, '-y', '-loglevel', SAVE_VIDEO_LOG_LEVEL,
        '-f', 'rawvideo',
        '-pix_fmt', 'rgba' if n_comp == 4 else 'rgb24',
        '-s', f'{width}x{height}',
        '-r', str(fps),
        '-i', '-',
        '-an',
    ]

    if pix_fmt not in _NO_SUBSAMPLE_FMTS:
        cmd += ['-vf', _EVEN_FILTER]
    cmd += [
        '-c:v', codec,
        '-preset', cfg['preset'],
        '-crf', str(cfg['crf']),
        '-pix_fmt', pix_fmt,
    ]

    if pix_fmt.startswith('yuv444'):
        cmd += ['-profile:v', 'high444']
    if SAVE_VIDEO_FASTSTART and path.lower().endswith('.mp4'):
        cmd += ['-movflags', '+faststart']
    cmd.append(path)
    return cmd

class VideoWriter:

    def __init__(self, path: str, width: int, height: int, fps: int,
                 quality: str = SAVE_QUALITY):
        self._path = path
        self._width = width
        self._height = height
        self._fps = fps
        self._quality = quality
        self._proc = None
        self._n_written = 0
        self._failed = False

    @property
    def path(self) -> str:
        return self._path

    @property
    def frames_written(self) -> int:
        return self._n_written

    def _start(self, n_comp: int) -> None:
        cmd = build_ffmpeg_command(
            self._path, self._width, self._height, self._fps,
            n_comp, self._quality,
        )
        logger.info('ffmpeg encode start: %s', ' '.join(cmd))
        self._proc = subprocess.Popen(
            cmd, stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
        )

    def write(self, img: np.ndarray) -> None:
        if self._failed:
            return
        frame = np.ascontiguousarray(img[::-1])
        if self._proc is None:
            self._start(frame.shape[2] if frame.ndim == 3 else 3)
        try:
            self._proc.stdin.write(frame.tobytes())
        except (BrokenPipeError, OSError) as exc:
            self._failed = True
            logger.error('ffmpeg pipe write failed: %s', exc)
            self._drain_stderr()
            return
        self._n_written += 1

    def _drain_stderr(self) -> None:
        if self._proc is None or self._proc.stderr is None:
            return
        err = self._proc.stderr.read()
        if err:
            logger.error('ffmpeg: %s', err.decode(errors='replace').strip())

    def close(self) -> None:
        if self._proc is None:
            return
        try:
            self._proc.stdin.close()
        except (BrokenPipeError, OSError):
            pass
        self._drain_stderr()
        code = self._proc.wait()
        self._proc = None
        if code != 0:
            logger.error('ffmpeg exited with code %d', code)
            return
        logger.info(
            'Video saved: %s (%d frames, %d fps, quality=%s)',
            self._path, self._n_written, self._fps, self._quality,
        )

def check_ffmpeg() -> bool:
    return shutil.which(FFMPEG_BIN) is not None
