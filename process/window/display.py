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
    from configs.settings import WINDOW_WIDTH, WINDOW_HEIGHT

    from configs.settings import WINDOW_ASPECT_RATIO

    mon_w, mon_h = _get_monitor_resolution(monitor_index)
    if mon_w > 0 and mon_h > 0:
        if WINDOW_WIDTH > mon_w or WINDOW_HEIGHT > mon_h:
            rec_w = min(mon_w, round(mon_h / WINDOW_ASPECT_RATIO))
            rec_h = round(rec_w * WINDOW_ASPECT_RATIO)
            logger.warning(
                'get_window_sizes: configured %dx%d exceeds monitor %dx%d'
                ' — recommended WINDOW_WIDTH=%d (-> %dx%d)',
                WINDOW_WIDTH, WINDOW_HEIGHT, mon_w, mon_h, rec_w, rec_w, rec_h,
            )

    return WINDOW_WIDTH, WINDOW_HEIGHT

def capture_frame(plotter) -> np.ndarray:
    from configs.settings import SAVE_ALPHA
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
    ).reshape(h, w, n_comp)
    logger.debug('capture_frame: %dx%d n_comp=%d', w, h, n_comp)
    return arr

class PBOCapture:

    def __init__(
        self,
        render_window,
        w: int,
        h: int,
        n_comp: int = 3,
    ) -> None:
        from OpenGL.GL import (
            glGenBuffers, glBindBuffer, glBufferData,
            GL_PIXEL_PACK_BUFFER, GL_STREAM_READ,
        )
        self._rw = render_window
        self._w, self._h, self._n_comp = w, h, n_comp
        self._size = w * h * n_comp
        _ids = glGenBuffers(2)
        self._pbos = [int(_ids[0]), int(_ids[1])]
        for pbo in self._pbos:
            glBindBuffer(GL_PIXEL_PACK_BUFFER, pbo)
            glBufferData(
                GL_PIXEL_PACK_BUFFER, self._size, None, GL_STREAM_READ,
            )
        glBindBuffer(GL_PIXEL_PACK_BUFFER, 0)
        self._submit_idx = 0
        self._pending: int | None = None

    def submit(self) -> None:
        from OpenGL.GL import (
            glBindBuffer, glReadPixels,
            GL_PIXEL_PACK_BUFFER, GL_RGB, GL_RGBA, GL_UNSIGNED_BYTE,
        )
        self._rw.MakeCurrent()
        pbo = self._pbos[self._submit_idx]
        gl_fmt = GL_RGBA if self._n_comp == 4 else GL_RGB
        glBindBuffer(GL_PIXEL_PACK_BUFFER, pbo)
        glReadPixels(
            0, 0, self._w, self._h, gl_fmt, GL_UNSIGNED_BYTE, 0,
        )
        glBindBuffer(GL_PIXEL_PACK_BUFFER, 0)
        self._pending = pbo
        self._submit_idx ^= 1

    def retrieve(self) -> np.ndarray | None:
        if self._pending is None:
            return None
        import ctypes
        from OpenGL.GL import (
            glBindBuffer, glMapBuffer, glUnmapBuffer,
            GL_PIXEL_PACK_BUFFER, GL_READ_ONLY,
        )
        self._rw.MakeCurrent()
        glBindBuffer(GL_PIXEL_PACK_BUFFER, self._pending)
        ptr = glMapBuffer(GL_PIXEL_PACK_BUFFER, GL_READ_ONLY)
        if isinstance(ptr, int):
            ptr = (ctypes.c_uint8 * self._size).from_address(ptr)
        arr = np.frombuffer(ptr, dtype=np.uint8).reshape(
            self._h, self._w, self._n_comp,
        ).copy()
        glUnmapBuffer(GL_PIXEL_PACK_BUFFER)
        glBindBuffer(GL_PIXEL_PACK_BUFFER, 0)
        self._pending = None
        return arr

    def destroy(self) -> None:
        if not self._pbos:
            return
        from OpenGL.GL import glDeleteBuffers
        glDeleteBuffers(len(self._pbos), self._pbos)
        self._pbos = []
        self._pending = None

def save_frame_to_disk(img: np.ndarray, fname: str) -> None:
    import cv2
    from configs.settings import SAVE_PNG_COMPRESSION, SAVE_JPEG_QUALITY
    img = img[::-1].copy()
    _ext = str(fname).rsplit('.', 1)[-1].lower()
    if _ext in ('jpg', 'jpeg'):
        params = [cv2.IMWRITE_JPEG_QUALITY, SAVE_JPEG_QUALITY]
        converted = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
    elif img.shape[2] == 4:
        params = [cv2.IMWRITE_PNG_COMPRESSION, SAVE_PNG_COMPRESSION]
        alpha = img[:, :, 3:4].astype(np.float32) / 255.0
        rgb = (
            img[:, :, :3].astype(np.float32) * alpha
        ).clip(0, 255).astype(np.uint8)
        img = np.concatenate([rgb, img[:, :, 3:4]], axis=2)
        converted = cv2.cvtColor(img, cv2.COLOR_RGBA2BGRA)
    else:
        params = [cv2.IMWRITE_PNG_COMPRESSION, SAVE_PNG_COMPRESSION]
        converted = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
    cv2.imwrite(str(fname), converted, params)
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
