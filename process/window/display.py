import re
import logging
import subprocess
import numpy as np
import vtk
from vtk.util.numpy_support import vtk_to_numpy

logger = logging.getLogger(__name__)

def _get_monitor_resolution(monitor_index: int) -> tuple[int, int]:
    try:
        xr = subprocess.check_output(['xrandr'], text=True)
        monitors = re.findall(
            r'connected\s+(?:primary\s+)?(\d+)x(\d+)\+(-?\d+)\+(-?\d+)',
            xr,
        )
        if monitors:
            idx = min(monitor_index, len(monitors) - 1)
            return int(monitors[idx][0]), int(monitors[idx][1])
        logger.warning('xrandr: no monitors found')
    except OSError:
        logger.warning('xrandr not available')
    return 0, 0

def get_window_sizes(monitor_index: int = 0) -> tuple[int, int]:
    from configs.defaults import WINDOW_WIDTH, WINDOW_HEIGHT

    from configs.defaults import WINDOW_ASPECT_RATIO

    mon_w, mon_h = _get_monitor_resolution(monitor_index)
    if mon_w > 0 and mon_h > 0:
        if WINDOW_WIDTH > mon_w or WINDOW_HEIGHT > mon_h:
            rec_w = min(mon_w, round(mon_h / WINDOW_ASPECT_RATIO))
            rec_h = round(rec_w * WINDOW_ASPECT_RATIO)
            logger.warning(
                'get_window_sizes: configured %dx%d exceeds monitor %dx%d'
                ' — recommended WINDOW_WIDTH=%d (→ %dx%d)',
                WINDOW_WIDTH, WINDOW_HEIGHT, mon_w, mon_h, rec_w, rec_w, rec_h,
            )

    return WINDOW_WIDTH, WINDOW_HEIGHT

def capture_frame(plotter) -> np.ndarray:
    from configs.defaults import SAVE_ALPHA
    w2if = vtk.vtkWindowToImageFilter()
    w2if.SetInput(plotter.render_window)
    if SAVE_ALPHA:
        w2if.SetInputBufferTypeToRGBA()
    else:
        w2if.SetInputBufferTypeToRGB()
    w2if.ReadFrontBufferOff()
    w2if.Update()
    output = w2if.GetOutput()
    w, h, _ = output.GetDimensions()
    n_comp = output.GetPointData().GetScalars().GetNumberOfComponents()
    arr = vtk_to_numpy(
        output.GetPointData().GetScalars()
    ).reshape(h, w, n_comp)[::-1].copy()
    logger.debug('capture_frame: %dx%d n_comp=%d', w, h, n_comp)
    return arr

def save_frame_to_disk(img: np.ndarray, fname: str) -> None:
    import cv2
    if img.shape[2] == 4:
        cv2.imwrite(str(fname), cv2.cvtColor(img, cv2.COLOR_RGBA2BGRA))
    else:
        cv2.imwrite(str(fname), cv2.cvtColor(img, cv2.COLOR_RGB2BGR))
    logger.debug('save_frame_to_disk: %s', fname)

def save_screenshot(plotter, fname: str = None):
    plotter.render()
    img = capture_frame(plotter)
    if fname is not None:
        save_frame_to_disk(img, fname)
        logger.debug('save_screenshot: %s', fname)
        return None
    return img

def center_window(plotter, monitor_index=0):
    if hasattr(plotter, 'app_window') and plotter.app_window is not None:
        app_win = plotter.app_window
        ww = app_win.width()
        wh = app_win.height()
        screens = app_win.screen().virtualSiblings()
        idx = min(monitor_index, len(screens) - 1)
        geom = screens[idx].availableGeometry()
        mw, mh = geom.width(), geom.height()
        x = geom.x() + max(0, (mw - ww) // 2)
        y = geom.y() + max(0, (mh - wh) // 2)
        app_win.move(x, y)
        logger.info(
            'Window placed (Qt): monitor=%d pos=(%d,%d)'
            ' win=%dx%d screen=%dx%d',
            idx, x, y, ww, wh, mw, mh,
        )
        return

    try:
        xr = subprocess.check_output(['xrandr'], text=True)
        monitors = re.findall(
            r'connected\s+(?:primary\s+)?(\d+)x(\d+)\+(-?\d+)\+(-?\d+)',
            xr,
        )
        if not monitors:
            logger.warning('xrandr: no monitors found')
            return
        idx = min(monitor_index, len(monitors) - 1)
        pw, ph, px, py = (int(v) for v in monitors[idx])
        ww, wh = plotter.render_window.GetSize()
        x = px + max(0, (pw - ww) // 2)
        y = py + max(0, (ph - wh) // 2)
        plotter.render_window.SetPosition(x, y)
        logger.info(
            'Window placed (VTK): monitor=%d pos=(%d,%d)'
            ' win=%dx%d screen=%dx%d',
            idx, x, y, ww, wh, pw, ph,
        )
    except OSError:
        logger.warning('xrandr not available, centering skipped')
