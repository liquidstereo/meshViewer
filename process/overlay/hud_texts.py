import time
import threading
import logging
import vtk
import configs.settings as _cfg

from configs.system_resources import get_system_info, get_gpu_info
from configs.settings import (
    UI_FONT_FAMILY,
    UI_STATUS_LINE_SPACING,
    UI_STATUS_COLOR, UI_STATUS_PAD_PX, UI_STATUS_PAD_PY,
    UI_MODE_COLOR,
    UI_MODE_PAD_PX, MODE_MSG_DURATION,
    UI_LOG_COLOR, UI_LOG_ERROR_COLOR,
    UI_LOG_PAD_PX, UI_LOG_PAD_PY,
    UI_HELP_COLOR,
    UI_HELP_BG_OPACITY,
    UI_COLORBAR_WIDTH, UI_COLORBAR_HEIGHT,
    UI_COLORBAR_POS_X, UI_COLORBAR_POS_Y,
    UI_COLORBAR_FONT_FAMILY,
    UI_COLORBAR_TITLE_COLOR, UI_COLORBAR_LABEL_COLOR,
    UI_COLORBAR_NLABELS, UI_COLORBAR_BAR_RATIO,
    ERROR_MSG_DURATION,
    LOG_FORMAT, LOG_MSEC_FORMAT,
)
from process.mode.common import _hex_to_rgb, _set_font_family

logger = logging.getLogger(__name__)

def _get_hud_renderer(plotter):
    return getattr(plotter, '_hud_renderer', plotter.renderer)

_HELP_TEXT = (
    'SPACE      Play / Pause\n'
    'Left/Right Frame Step\n'
    'Up / Down  First / Last Frame\n'
    '`          Screenshot\n'
    '1          Grid + BBox\n'
    'q          Default Mesh\n'
    's          Smooth Shading\n'
    '2          Vtx Labels / Pt.RGB toggle\n'
    '3          Wireframe\n'
    '4          Smooth+PBR+Tex (cycle)\n'
    '5          Isoline\n'
    'd          Mesh Reduction\n'
    '6          Surface Normal\n'
    '7          Mesh Quality\n'
    '8          Face Normal\n'
    '9          Depth\n'
    'e          Edge Extract\n'
    'b          Backface\n'
    'c          Parallel / Perspective\n'
    'F11        Theme Toggle (black/white)\n'
    'F12        Actor Visibility Cycle\n'
    'F1         Front View\n'
    'F2         Back View\n'
    'F3         Side Left View\n'
    'F4         Side Right View\n'
    'F5         Top View\n'
    'F6         Bottom View\n'
    'KP+ / -    Inc. / Dec. (Pt. Size)\n'
    'KP 7 / 9   Zoom In / Out (scale)\n'
    'KP 1 / 3   Dolly In / Out (move)\n'
    'PgUp/Dn    Axis / Smooth Cycle\n'
    'KP 4 / 6   Rotate Y\n'
    'KP 2 / 8   Rotate X\n'
    'Ctrl+KP4/6 Truck L / R\n'
    'Ctrl+KP8/2 Pedestal U / D\n'
    'KP 5       Center View\n'
    'KP .       Turntable\n'
    'r / KP0    Cam. Reset\n'
    'BackSpace  Full Reset\n'
    '/          Toggle Info\n'
    ',          Toggle Status Text\n'
    '.          Toggle Log Overlay\n'
    'Escape     Quit\n'
    'H          Hide Help'
)

class _LastMessageHandler(logging.Handler):

    def __init__(self):
        super().__init__()
        self.last_message = ''
        self.last_level = logging.DEBUG

    def emit(self, record):
        self.last_message = self.format(record)
        self.last_level = record.levelno

def init_status_text(plotter) -> None:
    _, win_h = plotter.window_size

    actor = vtk.vtkTextActor()
    prop = actor.GetTextProperty()
    _set_font_family(prop, UI_FONT_FAMILY)
    prop.SetFontSize(_cfg.UI_STATUS_FONT_SIZE)
    prop.SetLineSpacing(UI_STATUS_LINE_SPACING)
    prop.SetJustificationToLeft()
    prop.SetVerticalJustificationToTop()
    prop.SetColor(*_hex_to_rgb(UI_STATUS_COLOR))

    coord = actor.GetPositionCoordinate()
    coord.SetCoordinateSystemToDisplay()
    coord.SetValue(UI_STATUS_PAD_PX, win_h - UI_STATUS_PAD_PY)

    actor.SetInput('')
    _get_hud_renderer(plotter).AddActor2D(actor)
    plotter._status_actor = actor
    logger.debug('init_status_text: actor registered')

def update_status_text(plotter, idx: int, total: int, fps: float) -> None:
    actor = getattr(plotter, '_status_actor', None)
    if actor is None:
        return
    if not getattr(plotter, '_is_status_visible', True):
        actor.SetInput('')
        return
    n_pts = getattr(plotter, '_n_points', 0)
    n_fc = getattr(plotter, '_n_faces', 0)
    n_cells = getattr(plotter, '_n_cells', 0)

    is_point_cloud = n_pts > 0 and n_fc == 0 and n_cells == 0

    cam = plotter.renderer.GetActiveCamera()
    cx, cy, cz = cam.GetPosition()
    fl = cam.GetDistance()
    is_parallel = cam.GetParallelProjection()
    mode_str = 'Parallel' if is_parallel else 'Perspective'
    zoom = cam.GetParallelScale() if is_parallel else cam.GetViewAngle()

    if is_point_cloud:
        elem_info = f'POINTS: {n_pts:,}'
    else:
        elem_info = f'VERTICES: {n_pts:,} TRIANGLES: {n_fc:,}'

    sysinfo = getattr(plotter, '_sysinfo_cache', None)
    sys_line = 'SYS.INFO: LOADING SYSTEM INFO...'
    if sysinfo is not None:
        sys_line = (
            f'CPU: {sysinfo["cpu_percent"]:.1f}%'
            f' . MEM: {sysinfo["memory_percent"]:.1f}%'
        )
        gpu = getattr(plotter, '_gpuinfo_cache', None)
        if gpu is not None:
            sys_line += (
                f' . GPU: {gpu["gpu_percent"]:.1f}%'
                f' . VRAM: {gpu["vram_percent"]:.1f}%'
            )

    is_backface = getattr(plotter, '_is_backface', False)
    is_point_cloud = getattr(plotter, '_n_faces', 1) == 0
    if is_point_cloud:
        pt_fog = getattr(plotter, '_pt_fog_enabled', False)
        cull_label = f'POINT.FOG: {"ON" if pt_fog else "OFF"}'
    else:
        cull_label = f'BACKFACE.CULLING: {"ON" if is_backface else "OFF"}'

    input_name = getattr(
        plotter, '_input_path',
        getattr(plotter, '_input_name', ''),
    )
    audio_fps = getattr(plotter, '_audio_fps', None)
    if audio_fps is not None and audio_fps > 0:
        total_sec = idx // audio_fps
        mm = total_sec // 60
        ss = total_sec % 60
        ff = idx % audio_fps
        time_part = f'| {mm:02d}:{ss:02d}:{ff:02d}'
    else:
        time_part = ''
    status = (
        f'FRAME. {idx:04d}/{total - 1:04d} | FPS: {fps:.3f}\n'

        f'—\n'
        f'SYS.INFO: {sys_line}\n'
        f'INPUT: {input_name} {time_part}\n'
        f'—\n'
        f'{elem_info}\n'
        f'{cull_label}\n'
        f'{mode_str.upper()}.CAM: {cx:.3f}, {cy:.3f}, {cz:.3f}\n'
        f'FOCAL.LENGTH: {fl:.3f}\n'
        f'ZOOM: {zoom:.3f}'
    )
    actor.SetInput(status)

def init_mode_text(plotter) -> None:
    win_w, win_h = plotter.window_size

    actor = vtk.vtkTextActor()
    prop = actor.GetTextProperty()
    _set_font_family(prop, UI_FONT_FAMILY)
    prop.SetFontSize(_cfg.UI_MODE_FONT_SIZE)
    prop.SetBold(True)
    prop.SetJustificationToRight()
    prop.SetVerticalJustificationToTop()
    prop.SetColor(*_hex_to_rgb(UI_MODE_COLOR))

    coord = actor.GetPositionCoordinate()
    coord.SetCoordinateSystemToDisplay()
    coord.SetValue(win_w - UI_MODE_PAD_PX, win_h - UI_STATUS_PAD_PY)

    actor.SetInput('')
    _get_hud_renderer(plotter).AddActor2D(actor)

    plotter._mode_actor = actor
    logger.debug('init_mode_text: actor registered')

def update_mode_text(plotter, curr_time: float) -> None:
    actor = getattr(plotter, '_mode_actor', None)
    if actor is None:
        return
    msg_time = getattr(plotter, '_mode_msg_time', 0.0)
    if curr_time - msg_time > MODE_MSG_DURATION:
        actor.SetInput('')
    else:
        actor.SetInput(getattr(plotter, '_mode_msg', ''))

def init_log_overlay(plotter) -> None:

    handler = _LastMessageHandler()
    handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter(LOG_FORMAT)
    formatter.default_msec_format = LOG_MSEC_FORMAT
    handler.setFormatter(formatter)
    logging.getLogger().addHandler(handler)
    plotter._log_handler = handler

    actor = vtk.vtkTextActor()
    prop = actor.GetTextProperty()
    _set_font_family(prop, UI_FONT_FAMILY)
    prop.SetFontSize(_cfg.UI_LOG_FONT_SIZE)
    prop.SetJustificationToLeft()
    prop.SetVerticalJustificationToBottom()
    prop.SetColor(*_hex_to_rgb(UI_LOG_COLOR))

    coord = actor.GetPositionCoordinate()
    coord.SetCoordinateSystemToDisplay()
    coord.SetValue(UI_LOG_PAD_PX, UI_LOG_PAD_PY)

    actor.SetInput('')
    _get_hud_renderer(plotter).AddActor2D(actor)
    plotter._log_actor = actor
    logger.debug('init_log_overlay: actor registered')

def update_log_overlay(plotter) -> None:
    actor = getattr(plotter, '_log_actor', None)
    handler = getattr(plotter, '_log_handler', None)
    if actor is None or handler is None:
        return
    if not getattr(plotter, '_is_log_visible', True):
        actor.SetInput('')
        return
    prop = actor.GetTextProperty()
    error_msg = getattr(plotter, '_error_msg', '')
    error_time = getattr(plotter, '_error_msg_time', 0.0)
    now = time.time()
    if error_msg and (now - error_time) < ERROR_MSG_DURATION:
        actor.SetInput(error_msg)
        prop.SetColor(*_hex_to_rgb(UI_LOG_ERROR_COLOR))
    else:
        actor.SetInput(handler.last_message)
        if handler.last_level >= logging.ERROR:
            prop.SetColor(*_hex_to_rgb(UI_LOG_ERROR_COLOR))
        else:
            prop.SetColor(*_hex_to_rgb(UI_LOG_COLOR))

def init_help_overlay(plotter) -> None:
    win_w, win_h = plotter.window_size

    actor = vtk.vtkTextActor()
    prop = actor.GetTextProperty()
    _set_font_family(prop, UI_FONT_FAMILY)
    prop.SetFontSize(_cfg.UI_HELP_FONT_SIZE)
    prop.SetJustificationToLeft()
    prop.SetVerticalJustificationToBottom()
    prop.SetColor(*_hex_to_rgb(UI_HELP_COLOR))
    prop.SetBackgroundColor(0.0, 0.0, 0.0)
    prop.SetBackgroundOpacity(UI_HELP_BG_OPACITY)

    char_w = _cfg.UI_HELP_FONT_SIZE * 0.6
    char_h = _cfg.UI_HELP_FONT_SIZE * 1.4
    lines = _HELP_TEXT.split('\n')
    text_w = int(max(len(l) for l in lines) * char_w)
    text_h = int(len(lines) * char_h)
    pos_x = max(0, (win_w - text_w) // 2)
    pos_y = max(0, (win_h - text_h) // 2)

    coord = actor.GetPositionCoordinate()
    coord.SetCoordinateSystemToDisplay()
    coord.SetValue(pos_x, pos_y)

    actor.SetInput(_HELP_TEXT)
    actor.VisibilityOff()

    help_renderer = vtk.vtkRenderer()
    help_renderer.SetLayer(3)
    help_renderer.InteractiveOff()
    help_renderer.PreserveColorBufferOn()
    help_renderer.PreserveDepthBufferOn()
    rw = plotter.render_window
    rw.SetNumberOfLayers(max(rw.GetNumberOfLayers(), 4))
    rw.AddRenderer(help_renderer)
    help_renderer.AddActor2D(actor)

    plotter._help_actor = actor
    logger.debug('init_help_overlay: actor registered')

def init_colorbar(plotter) -> None:
    display_lut = vtk.vtkLookupTable()
    display_lut.Build()

    actor = vtk.vtkScalarBarActor()
    actor.SetLookupTable(display_lut)
    actor.SetOrientationToVertical()
    actor.SetWidth(UI_COLORBAR_WIDTH)
    actor.SetHeight(UI_COLORBAR_HEIGHT)
    actor.SetPosition(UI_COLORBAR_POS_X, UI_COLORBAR_POS_Y)
    actor.SetNumberOfLabels(UI_COLORBAR_NLABELS)
    actor.SetBarRatio(UI_COLORBAR_BAR_RATIO)
    actor.SetUnconstrainedFontSize(True)

    title_prop = actor.GetTitleTextProperty()
    _set_font_family(title_prop, UI_COLORBAR_FONT_FAMILY)

    if _cfg.UI_COLORBAR_TITLE_FONT_SIZE > 0:
        title_prop.SetFontSize(_cfg.UI_COLORBAR_TITLE_FONT_SIZE)
    else :
        title_prop.SetOpacity(0.0)

    title_prop.SetColor(*_hex_to_rgb(UI_COLORBAR_TITLE_COLOR))
    title_prop.BoldOff()
    title_prop.ItalicOff()
    title_prop.ShadowOff()

    label_prop = actor.GetLabelTextProperty()
    _set_font_family(label_prop, UI_COLORBAR_FONT_FAMILY)
    label_prop.SetFontSize(_cfg.UI_COLORBAR_LABEL_FONT_SIZE)
    label_prop.SetColor(*_hex_to_rgb(UI_COLORBAR_LABEL_COLOR))
    label_prop.BoldOff()
    label_prop.ItalicOff()
    label_prop.ShadowOff()

    actor.VisibilityOff()
    _get_hud_renderer(plotter).AddActor2D(actor)
    plotter._colorbar_actor = actor
    plotter._colorbar_display_lut = display_lut
    logger.debug('init_colorbar: actor registered')

def update_colorbar(plotter) -> None:
    actor = getattr(plotter, '_colorbar_actor', None)
    if actor is None:
        return
    if not getattr(plotter, '_is_colorbar', True):
        actor.VisibilityOff()
        return
    lut = getattr(plotter, '_cmap_lut', None)
    if lut is None:
        actor.VisibilityOff()
        return
    if not getattr(plotter, '_is_overlay_visible', True):
        return
    lo, hi = getattr(plotter, '_cmap_range', (0.0, 1.0))
    title = getattr(plotter, '_cmap_title', '')
    display_lut = plotter._colorbar_display_lut
    display_lut.DeepCopy(lut)
    display_lut.SetRange(lo, hi)
    display_lut.Build()
    actor.SetTitle(title)
    actor.VisibilityOn()

def _sysinfo_worker(plotter, stop_event: threading.Event) -> None:
    while not stop_event.is_set():
        plotter._sysinfo_cache = get_system_info()
        plotter._gpuinfo_cache = get_gpu_info()

def init_sysinfo_monitor(plotter) -> None:
    plotter._sysinfo_cache = None
    plotter._gpuinfo_cache = None
    stop = threading.Event()
    t = threading.Thread(
        target=_sysinfo_worker,
        args=(plotter, stop),
        daemon=True,
    )
    t.start()
    plotter._sysinfo_stop = stop
    plotter._sysinfo_thread = t
    logger.debug('init_sysinfo_monitor: thread started')

def init_overlay_text(
    plotter,
    name: str,
    text: str = '',
    position: str = 'left',
    padding_left: int = 10,
    padding_right: int = 10,
    padding_top: int | None = 30,
    padding_bottom: int | None = None,
    font_size: int = 12,
    color: str = '#FFFFFF',
) -> None:
    win_w, win_h = plotter.window_size

    if position == 'right':
        x = win_w - padding_right
    else:
        x = padding_left

    if padding_top is not None:
        y = win_h - padding_top
    elif padding_bottom is not None:
        y = padding_bottom
    else:
        y = win_h

    actor = vtk.vtkTextActor()
    prop = actor.GetTextProperty()
    prop.SetFontSize(font_size)
    _set_font_family(prop, UI_FONT_FAMILY)
    prop.SetColor(*_hex_to_rgb(color))
    if position == 'right':
        prop.SetJustificationToRight()
    else:
        prop.SetJustificationToLeft()
    if padding_bottom is not None:
        prop.SetVerticalJustificationToBottom()
    else:
        prop.SetVerticalJustificationToTop()
    prop.BoldOff()
    prop.ItalicOff()
    prop.ShadowOff()

    coord = actor.GetPositionCoordinate()
    coord.SetCoordinateSystemToDisplay()
    coord.SetValue(float(x), float(y), 0.0)

    actor.SetInput(text)
    _get_hud_renderer(plotter).AddActor2D(actor)

    if not hasattr(plotter, '_text_overlay_actors'):
        plotter._text_overlay_actors = {}
    plotter._text_overlay_actors[name] = actor
    logger.debug('init_overlay_text: "%s" registered', name)

def update_periodic_overlays(plotter) -> None:
    update_log_overlay(plotter)
    update_colorbar(plotter)

def update_overlay_text(plotter, name: str, text: str) -> None:
    actors = getattr(plotter, '_text_overlay_actors', {})
    actor = actors.get(name)
    if actor is None:
        logger.warning('update_overlay_text: "%s" not found', name)
        return
    actor.SetInput(text)
