import logging

from process.scene.grid import setup_grid, update_grid_bounds
from process.scene.axes import setup_axes_marker
from process.scene.actor import init_render_actor, init_actors
from process.scene.lighting import apply_lighting
from process.scene.hdri import setup_hdri, enable_hdri, disable_hdri, rotate_hdri

logger = logging.getLogger(__name__)

def setup_scene(plotter) -> None:
    setup_grid(plotter)
    if not getattr(plotter, '_is_grid', True):
        plotter.remove_bounds_axes()
    setup_axes_marker(plotter)
    logger.debug('setup_scene: grid and axes initialized')

__all__ = [
    'setup_grid', 'update_grid_bounds',
    'setup_axes_marker',
    'init_render_actor',
    'init_actors',
    'apply_lighting',
    'setup_hdri',
    'enable_hdri',
    'disable_hdri',
    'rotate_hdri',
    'setup_scene',
]
