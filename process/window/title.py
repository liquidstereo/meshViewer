import logging

from configs.settings import WINDOW_TITLE, WINDOW_TITLE_RECORDING

logger = logging.getLogger(__name__)

def format_title(name: str, recording: bool) -> str:
    if not recording:
        return WINDOW_TITLE
    return WINDOW_TITLE_RECORDING.format(title=WINDOW_TITLE, name=name)

def set_recording_title(plotter, recording: bool) -> None:
    rw = getattr(plotter, 'render_window', None)
    if rw is None or getattr(plotter, '_headless', False):
        return
    title = format_title(getattr(plotter, '_input_name', ''), recording)
    rw.SetWindowName(title)
    logger.debug('set_recording_title: %s', title)
