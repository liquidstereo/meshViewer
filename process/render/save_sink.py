import os
import logging

import numpy as np

from configs.settings import (
    SAVE_FILENAME_DIGITS, TARGET_ANIM_FPS, SAVE_QUALITY,
    SAVE_MODE_FILENAME,
)
from process.record import (
    VideoWriter, is_video_ext, resolve_output_path,
)
from process.window.display import save_frame_to_disk

logger = logging.getLogger(__name__)

class FrameSink:

    def __init__(self, save_path: str, stem: str, ext: str,
                 executor, width: int = 0, height: int = 0,
                 fps: int = TARGET_ANIM_FPS,
                 quality: str = SAVE_QUALITY):
        self._stem = stem
        self._ext = ext.lower().lstrip('.')
        self._executor = executor
        self._count = 0
        self._is_video = is_video_ext(self._ext)
        self._writer = None
        self._img_dir = save_path
        self._target = save_path
        if not self._is_video:
            os.makedirs(save_path, exist_ok=True)
            return
        out_dir = os.path.dirname(save_path.rstrip(os.sep)) or '.'
        os.makedirs(out_dir, exist_ok=True)

        self._target = resolve_output_path(out_dir, stem, self._ext)
        self._writer = VideoWriter(
            self._target, width, height, fps, quality,
        )

    @property
    def is_video(self) -> bool:
        return self._is_video

    @property
    def count(self) -> int:
        return self._count

    @property
    def target(self) -> str:
        return self._target

    @property
    def display_target(self) -> str:
        if self._is_video:
            return self._target
        return os.path.join(self._img_dir, self._stem)

    def _image_path(self) -> str:
        return os.path.join(
            self._img_dir,
            f'{self._stem}.{self._count:0{SAVE_FILENAME_DIGITS}d}'
            f'.{self._ext}',
        )

    def submit(self, img: np.ndarray) -> str:
        if self._is_video:
            self._writer.write(img)
            self._count += 1
            return self._target
        path = self._image_path()
        self._executor.submit(save_frame_to_disk, img, path)
        self._count += 1
        return path

    def close(self) -> None:
        if self._writer is not None:
            self._writer.close()
            self._writer = None

def resolve_stem(plotter) -> str:
    stem = getattr(plotter, '_input_name', 'frame')
    if not SAVE_MODE_FILENAME:
        return stem
    from process.plotter.state import current_mode_name
    mode = current_mode_name(plotter).replace('.', '_')
    return f'{stem}_{mode}' if mode else stem

def create_sink(plotter, save_path: str, executor) -> FrameSink:
    width, height = plotter.render_window.GetSize()
    sink = FrameSink(
        save_path,
        resolve_stem(plotter),
        getattr(plotter, '_save_ext', 'png'),
        executor, width, height, TARGET_ANIM_FPS,
        getattr(plotter, '_save_quality', SAVE_QUALITY),
    )
    logger.info(
        'Save sink: mode=%s target=%s fps=%d quality=%s size=%dx%d',
        'video' if sink.is_video else 'image_sequence',
        sink.target, TARGET_ANIM_FPS,
        getattr(plotter, '_save_quality', SAVE_QUALITY), width, height,
    )
    return sink

def format_saved_message(count: int, target: str) -> str:
    return (
        f'Saved {count} captured frames to "{os.path.relpath(target)}".'
    )
