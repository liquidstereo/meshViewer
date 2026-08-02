import os
import logging
import vtk

from configs.settings import (
    SEQ_IMAGE_EXTS, DISPLAY_SEQ_ROUND, SEQ_ROUND_SS,
)
from process.overlay.seq_geometry import (
    calc_viewport, viewport_px, scaled_radius,
    make_corner_alpha, build_alpha_image,
)

logger = logging.getLogger(__name__)

_MAX_READ_FAILS = 10

_IMAGE_HEADS = {
    '.png':  b'\x89PNG\r\n\x1a\n',
    '.jpg':  b'\xff\xd8',
    '.jpeg': b'\xff\xd8',
    '.bmp':  b'BM',
}
_IMAGE_TAILS = {
    '.png':  b'IEND',
    '.jpg':  b'\xff\xd9',
    '.jpeg': b'\xff\xd9',
}
_TAIL_SCAN_BYTES = 64

def _is_complete_image(path: str) -> bool:
    ext = os.path.splitext(path)[1].lower()
    head = _IMAGE_HEADS.get(ext)
    tail = _IMAGE_TAILS.get(ext)
    try:
        size = os.path.getsize(path)
        if size < 32:
            return False
        with open(path, 'rb') as fh:
            if head is not None and fh.read(len(head)) != head:
                return False
            if tail is None:
                return True
            fh.seek(-min(_TAIL_SCAN_BYTES, size), os.SEEK_END)
            return tail in fh.read()
    except OSError:
        return False

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
        self._fail_count = 0
        self._alpha_image = None

        rw = plotter.render_window
        win_w, win_h = rw.GetSize()
        self._win_w, self._win_h = win_w, win_h

        self._reader = _create_reader(self._files[0])
        self._reader.SetFileName(self._files[0])
        self._reader.Update()
        dims = self._reader.GetOutput().GetDimensions()
        img_w, img_h = max(1, dims[0]), max(1, dims[1])

        viewport = calc_viewport(win_w, win_h, img_w, img_h)
        self._viewport = viewport
        vp_px_w, vp_px_h = viewport_px(viewport, win_w, win_h)

        self._resize = vtk.vtkImageResize()
        self._resize.SetInputConnection(
            self._reader.GetOutputPort()
        )
        self._resize.SetResizeMethodToOutputDimensions()
        self._resize.SetOutputDimensions(vp_px_w, vp_px_h, 1)
        self._resize.Update()

        self._output = self._attach_rounding(vp_px_w, vp_px_h)

        self._actor = vtk.vtkImageActor()
        self._actor.GetMapper().SetInputConnection(
            self._output.GetOutputPort()
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

    def _refresh_alpha(self, vp_px_w, vp_px_h) -> int:
        radius = scaled_radius(self._win_w)
        self._alpha_image = build_alpha_image(
            make_corner_alpha(vp_px_w, vp_px_h, radius, SEQ_ROUND_SS)
        )

        self._alpha_src.SetOutput(self._alpha_image)
        self._alpha_src.Modified()
        return radius

    def _attach_rounding(self, vp_px_w, vp_px_h):
        if not DISPLAY_SEQ_ROUND or scaled_radius(self._win_w) <= 0:
            return self._resize

        n_comp = self._reader.GetOutput().GetNumberOfScalarComponents()
        if n_comp < 3:
            logger.warning(
                'SequenceOverlay: rounding skipped'
                ' (%d-component image, RGB required).', n_comp,
            )
            return self._resize

        self._rgb = vtk.vtkImageExtractComponents()
        self._rgb.SetInputConnection(self._resize.GetOutputPort())
        self._rgb.SetComponents(0, 1, 2)

        self._alpha_src = vtk.vtkTrivialProducer()
        self._append = vtk.vtkImageAppendComponents()
        self._append.SetInputConnection(0, self._rgb.GetOutputPort())
        radius = self._refresh_alpha(vp_px_w, vp_px_h)
        self._append.AddInputConnection(0, self._alpha_src.GetOutputPort())
        self._append.Update()
        logger.info(
            'SequenceOverlay: rounding radius=%dpx ss=%d',
            radius, SEQ_ROUND_SS,
        )
        return self._append

    def sync_scale(self) -> bool:
        rw = self._renderer.GetRenderWindow()
        if rw is None or not self._files:
            return False
        win_w, win_h = rw.GetSize()
        if win_w == self._win_w and win_h == self._win_h:
            return False
        self._win_w, self._win_h = win_w, win_h

        dims = self._reader.GetOutput().GetDimensions()
        viewport = calc_viewport(
            win_w, win_h, max(1, dims[0]), max(1, dims[1]),
        )
        self._viewport = viewport
        self._renderer.SetViewport(*viewport)

        vp_px_w, vp_px_h = viewport_px(viewport, win_w, win_h)
        self._resize.SetOutputDimensions(vp_px_w, vp_px_h, 1)
        self._resize.Update()
        if self._alpha_image is not None:
            self._refresh_alpha(vp_px_w, vp_px_h)
        self._output.Update()
        self._fit_camera()
        logger.debug(
            'SequenceOverlay rescaled: win=%dx%d output=%dx%d',
            win_w, win_h, vp_px_w, vp_px_h,
        )
        return True

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

    def _reset_reader(self, path: str) -> None:
        self._reader = _create_reader(path)
        self._resize.SetInputConnection(self._reader.GetOutputPort())
        self._last_file = None

    def _read_image(self, path: str) -> bool:
        if not os.path.isfile(path):
            logger.error(
                'Sequence image missing: %s', os.path.basename(path),
            )
            return False
        if self._reader.CanReadFile(path) == 0:
            logger.error(
                'Sequence image unreadable: %s', os.path.basename(path),
            )
            return False

        if not _is_complete_image(path):
            logger.error(
                'Sequence image incomplete (truncated): %s',
                os.path.basename(path),
            )
            return False
        self._reader.SetFileName(path)
        self._reader.Modified()
        self._reader.Update()
        code = self._reader.GetErrorCode()
        if code != 0:
            logger.error(
                'Sequence image read failed (vtk error %d): %s',
                code, os.path.basename(path),
            )
            self._reset_reader(path)
            return False
        dims = self._reader.GetOutput().GetDimensions()
        if dims[0] < 1 or dims[1] < 1:
            logger.error(
                'Sequence image has empty extent %s: %s',
                dims, os.path.basename(path),
            )
            self._reset_reader(path)
            return False
        return True

    def _on_read_failure(self) -> None:
        self._fail_count += 1
        if self._fail_count < _MAX_READ_FAILS:
            return
        logger.error(
            'Sequence overlay disabled after %d read failures.',
            self._fail_count,
        )
        self.set_visible(False)
        self._files = []

    def update(self, idx: int) -> None:
        n = len(self._files)
        if n == 0:
            return
        file_idx = min(idx, n - 1)
        current_file = self._files[file_idx]
        if current_file == self._last_file:
            return
        self._last_file = current_file
        if not self._read_image(current_file):
            self._on_read_failure()
            return
        self._fail_count = 0
        self._resize.Modified()
        self._output.Update()

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
