import os
import logging
import vtk

from configs.defaults import (
    SEQ_SIZE_W, SEQ_SIZE_H,
    SEQ_PAD_RIGHT_PX, SEQ_PAD_BOTTOM_PX,
    SEQ_IMAGE_EXTS,
)

logger = logging.getLogger(__name__)

_READER_MAP = {
    '.png':  vtk.vtkPNGReader,
    '.jpg':  vtk.vtkJPEGReader,
    '.jpeg': vtk.vtkJPEGReader,
    '.bmp':  vtk.vtkBMPReader,
}

def _create_reader(filename):
    ext = os.path.splitext(filename)[1].lower()
    cls = _READER_MAP.get(ext, vtk.vtkPNGReader)
    return cls()

def _calc_viewport(win_w, win_h):
    pad_r = SEQ_PAD_RIGHT_PX / max(1, win_w)
    pad_b = SEQ_PAD_BOTTOM_PX / max(1, win_h)
    return (
        1.0 - SEQ_SIZE_W - pad_r,
        pad_b,
        1.0 - pad_r,
        SEQ_SIZE_H + pad_b,
    )

def _viewport_px(viewport, win_w, win_h):
    w = max(1, int((viewport[2] - viewport[0]) * win_w))
    h = max(1, int((viewport[3] - viewport[1]) * win_h))
    return w, h

class SequenceOverlay:

    def __init__(self, plotter, image_files):
        self._files = image_files

        rw = plotter.render_window
        win_w, win_h = rw.GetSize()
        viewport = _calc_viewport(win_w, win_h)
        self._viewport = viewport
        vp_px_w, vp_px_h = _viewport_px(viewport, win_w, win_h)

        self._reader = _create_reader(image_files[0])
        self._reader.SetFileName(image_files[0])
        self._reader.Update()

        self._resize = vtk.vtkImageResize()
        self._resize.SetInputConnection(
            self._reader.GetOutputPort()
        )
        self._resize.SetResizeMethodToOutputDimensions()
        self._resize.SetOutputDimensions(vp_px_w, vp_px_h, 1)
        self._resize.Update()

        self._actor = vtk.vtkImageActor()
        self._actor.GetMapper().SetInputConnection(
            self._resize.GetOutputPort()
        )

        self._renderer = vtk.vtkRenderer()
        self._renderer.SetLayer(1)
        self._renderer.SetViewport(*viewport)
        self._renderer.SetBackground(0.0, 0.0, 0.0)
        self._renderer.InteractiveOff()
        self._renderer.AddActor(self._actor)

        rw = plotter.render_window
        rw.SetNumberOfLayers(max(rw.GetNumberOfLayers(), 2))
        rw.AddRenderer(self._renderer)
        self._fit_camera()
        logger.info(
            'SequenceOverlay init: %d images, '
            'output=%dx%d viewport=%s',
            len(image_files), vp_px_w, vp_px_h, viewport,
        )

    def _fit_camera(self):
        self._actor.Update()
        bounds = self._actor.GetBounds()
        w = bounds[1] - bounds[0]
        h = bounds[3] - bounds[2]
        if w <= 0 or h <= 0:
            return

        cx = (bounds[0] + bounds[1]) / 2.0
        cy = (bounds[2] + bounds[3]) / 2.0

        camera = self._renderer.GetActiveCamera()
        camera.ParallelProjectionOn()
        camera.SetFocalPoint(cx, cy, 0.0)
        camera.SetPosition(cx, cy, 1.0)
        camera.SetViewUp(0.0, 1.0, 0.0)

        rw = self._renderer.GetRenderWindow()
        win_w, win_h = rw.GetSize()
        vp = self._viewport
        vp_w = max(1.0, (vp[2] - vp[0]) * win_w)
        vp_h = max(1.0, (vp[3] - vp[1]) * win_h)
        vp_aspect = vp_w / vp_h
        img_aspect = w / h

        if vp_aspect >= img_aspect:
            camera.SetParallelScale(h / 2.0)
        else:
            camera.SetParallelScale(w / (2.0 * vp_aspect))

    def set_visible(self, visible: bool) -> None:
        if visible:
            self._renderer.DrawOn()
        else:
            self._renderer.DrawOff()

    def update(self, idx):
        if idx >= len(self._files):
            return
        self._reader.SetFileName(self._files[idx])
        self._reader.Update()
        self._resize.Update()
        self._fit_camera()

def init_sequence_overlay(plotter, image_files):
    if not image_files:
        logger.warning('SequenceOverlay: no image files found.')
        return
    plotter._seq_overlay = SequenceOverlay(plotter, image_files)
    logger.info(
        'SequenceOverlay registered: %d frames.',
        len(image_files),
    )

def load_seq_files(args, total: int) -> list:
    if not args.images or not os.path.isdir(args.images):
        if args.images:
            logger.warning(
                'Image sequence dir not found: %s', args.images
            )
        return []
    seq_files = sorted(
        os.path.join(args.images, f)
        for f in os.listdir(args.images)
        if os.path.splitext(f)[1].lower() in SEQ_IMAGE_EXTS
    )
    if len(seq_files) != total:
        logger.warning(
            'Sequence image count (%d) != mesh count (%d)',
            len(seq_files), total,
        )
    return seq_files
