import logging
from pyvista.plotting import Plotter

from configs.defaults import (
    WINDOW_TITLE, WINDOW_MONITOR_INDEX,
    RENDER_MSAA_SAMPLES, RENDER_LINE_SMOOTHING, RENDER_POINT_SMOOTHING,
    TARGET_ANIM_FPS,
)
from process.window.display import get_window_sizes

logger = logging.getLogger(__name__)

def build_plotter() -> Plotter:
    win_w, win_h = get_window_sizes(WINDOW_MONITOR_INDEX)
    plotter = Plotter(
        title=WINDOW_TITLE,
        window_size=[win_w, win_h],
    )
    rw = plotter.render_window
    rw.SetMultiSamples(RENDER_MSAA_SAMPLES)
    rw.SetLineSmoothing(RENDER_LINE_SMOOTHING)
    rw.SetPointSmoothing(RENDER_POINT_SMOOTHING)
    rw.SetDesiredUpdateRate(0.001)
    object.__setattr__(plotter, 'pickpoint', None)
    logger.debug('build_plotter: %dx%d', win_w, win_h)
    return plotter
