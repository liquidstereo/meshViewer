import logging

from configs.settings import SAVE_PBO_ENABLED

logger = logging.getLogger(__name__)

REASON_DISABLED = 'SAVE_PBO_ENABLED=False'
REASON_HEADLESS = 'offscreen render target'
REASON_MSAA = 'MSAA enabled'

def pbo_skip_reason(plotter) -> str:
    if not SAVE_PBO_ENABLED:
        return REASON_DISABLED
    if getattr(plotter, '_headless', False):
        return REASON_HEADLESS
    if plotter.render_window.GetMultiSamples() != 0:
        return REASON_MSAA
    return ''

def use_pbo_capture(plotter, saving: bool) -> bool:
    return bool(saving) and not pbo_skip_reason(plotter)
