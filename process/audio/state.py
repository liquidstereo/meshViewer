import os
import time
import logging
from dataclasses import dataclass, field

from configs.defaults import (
    DEFAULT_BACKFACE, DEFAULT_COLORBAR, DEFAULT_LIGHTING,
    AUDIO_TARGET_FPS, AUDIO_GRID_Y_MAX,
)

logger = logging.getLogger(__name__)

@dataclass
class AudioContext:

    mag_t:        object
    total_frames: int
    x_grid:       object
    record_dir:   str | None
    is_recording: bool
    base_name:    str
    continuous:   bool
    grid_actor:   object = None

    start_time:   float = field(default_factory=time.time)

    paused:       bool  = False
    seek_delta:   int   = 0
    save_counter: int   = 0
    tab_state:    int   = 0
    monitor_ctx:  list  = field(default_factory=lambda: [None, None])
    executor:     object = None

def init_audio_state(
    plotter,
    audio_path: str,
    renderer,
    args,
    total_frames: int,
    mag_t,
    x_grid,
    grid_actor,
) -> 'AudioContext':
    record_dir = args.save
    base_name = os.path.splitext(os.path.basename(audio_path))[0]

    plotter._cmap_lut   = renderer._lut
    plotter._cmap_range = (0.0, AUDIO_GRID_Y_MAX)
    plotter._cmap_title = ''
    plotter._input_name = os.path.relpath(audio_path)
    plotter._input_path = plotter._input_name
    plotter._is_backface  = DEFAULT_BACKFACE
    plotter._is_colorbar  = DEFAULT_COLORBAR
    plotter._is_lighting  = DEFAULT_LIGHTING
    plotter._audio_fps    = AUDIO_TARGET_FPS

    return AudioContext(
        mag_t=mag_t,
        total_frames=total_frames,
        x_grid=x_grid,
        record_dir=record_dir,
        is_recording=(record_dir is not None),
        base_name=base_name,
        continuous=getattr(args, 'continuous', False),
        grid_actor=grid_actor,
    )
