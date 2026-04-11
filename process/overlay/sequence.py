import os
import logging
import vtk

from configs.defaults import (
    SEQ_SIZE_W,
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

def _calc_viewport(win_w, win_h, img_w, img_h):
    pad_r = SEQ_PAD_RIGHT_PX / max(1, win_w)
    pad_b = SEQ_PAD_BOTTOM_PX / max(1, win_h)
    vp_h_px = SEQ_SIZE_W * win_w * max(1, img_h) / max(1, img_w)
    seq_size_h = vp_h_px / max(1, win_h)
    return (
        1.0 - SEQ_SIZE_W - pad_r,
        pad_b,
        1.0 - pad_r,
        seq_size_h + pad_b,
    )

def _viewport_px(viewport, win_w, win_h):
    w = max(1, int((viewport[2] - viewport[0]) * win_w))
    h = max(1, int((viewport[3] - viewport[1]) * win_h))
    return w, h

class SequenceOverlay:

    def __init__(self, plotter, image_files, total_frames: int = 0):
        self._files = list(image_files)
        n = len(self._files)
        self._total_frames = total_frames if total_frames > 0 else n

        if n != self._total_frames:
            logger.warning(
                'SequenceOverlay: image count (%d) != mesh frames (%d). '
                'Direct index mapping applied; '
                'frames beyond image count will hold last image.',
                n, self._total_frames,
            )

        self._last_file = None

        rw = plotter.render_window
        win_w, win_h = rw.GetSize()

        self._reader = _create_reader(self._files[0])
        self._reader.SetFileName(self._files[0])
        self._reader.Update()
        dims = self._reader.GetOutput().GetDimensions()
        img_w, img_h = max(1, dims[0]), max(1, dims[1])

        viewport = _calc_viewport(win_w, win_h, img_w, img_h)
        self._viewport = viewport
        vp_px_w, vp_px_h = _viewport_px(viewport, win_w, win_h)

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
            n, vp_px_w, vp_px_h, viewport,
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

    def update(self, idx: int) -> None:
        n = len(self._files)
        if n == 0:
            return
        file_idx = min(idx, n - 1)
        current_file = self._files[file_idx]
        if current_file == self._last_file:
            return
        self._last_file = current_file
        self._reader.SetFileName(current_file)
        self._reader.Modified()
        self._reader.Update()
        self._resize.Modified()
        self._resize.Update()

def init_sequence_overlay(
    plotter, image_files, total_frames: int = 0
):
    if not image_files:
        logger.warning('SequenceOverlay: no image files found.')
        return
    plotter._seq_overlay = SequenceOverlay(
        plotter, image_files, total_frames
    )
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
    fs = int(getattr(args, 'frame_start', 0))
    fe_raw = getattr(args, 'frame_end', None)
    fe = int(fe_raw) if fe_raw is not None else None
    if fe is not None:
        seq_files = seq_files[fs:fe + 1]
    elif fs > 0:
        seq_files = seq_files[fs:]
    if len(seq_files) != total:
        logger.warning(
            'Sequence image count (%d) != mesh count (%d)',
            len(seq_files), total,
        )
    return seq_files
