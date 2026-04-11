import logging

logger = logging.getLogger(__name__)

_INFO_ACTORS = (
    '_status_actor',
    '_mode_actor',
    '_log_actor',
    '_help_actor',
    '_colorbar_actor',
)
_SCENE_ACTORS = (
    '_grid_actor',
    '_bbox_actor',
)

def toggle_info_overlay(plotter) -> None:
    plotter._is_overlay_visible = not getattr(
        plotter, '_is_overlay_visible', True
    )
    visible = plotter._is_overlay_visible

    _ALL_ACTORS = _INFO_ACTORS + _SCENE_ACTORS
    if not visible:
        plotter._overlay_prev_vis = {}
        for attr in _ALL_ACTORS:
            actor = getattr(plotter, attr, None)
            if actor is not None:
                plotter._overlay_prev_vis[attr] = bool(
                    actor.GetVisibility()
                )
                actor.VisibilityOff()
        _set_axes_visible(plotter, False)
    else:
        prev = getattr(plotter, '_overlay_prev_vis', {})
        for attr in _ALL_ACTORS:
            actor = getattr(plotter, attr, None)
            if actor is not None and prev.get(attr, True):
                actor.VisibilityOn()
        _set_axes_visible(plotter, True)

    seq = getattr(plotter, '_seq_overlay', None)
    if seq is not None:
        seq.set_visible(visible)

    logger.info(
        'toggle_info_overlay: overlay %s',
        'visible' if visible else 'hidden',
    )

def apply_overlay_visibility(plotter) -> None:
    if getattr(plotter, '_is_overlay_visible', True):
        return
    for attr in _INFO_ACTORS + _SCENE_ACTORS:
        actor = getattr(plotter, attr, None)
        if actor is not None:
            actor.VisibilityOff()
    _set_axes_visible(plotter, False)
    seq = getattr(plotter, '_seq_overlay', None)
    if seq is not None:
        seq.set_visible(False)
    logger.debug('apply_overlay_visibility: overlay hidden by --hide-info')

def _set_axes_visible(plotter, visible: bool) -> None:
    widget = getattr(plotter.renderer, 'axes_widget', None)
    if widget is None:
        return
    if visible:
        widget.EnabledOn()
    else:
        widget.EnabledOff()
