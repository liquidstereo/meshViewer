import logging

from configs.keybinding import KEY_SMOOTH, KEY_SMOOTH_SHADING
from process.mode.default import apply_default_reset
from process.scene.lighting import apply_lighting
from process.mode.labels import SMOOTH_CYCLE_LABELS, LBL_SURF_SMOOTHING
from process.scene.hdri import enable_hdri
from process.keys import bind_key

logger = logging.getLogger(__name__)

def register(p, trigger, set_mode):
    def _enter_tex_base(is_lighting: bool, pbr_with_tex: bool):
        p._is_smooth = True
        p._is_lighting = is_lighting
        p._is_tex = True
        p._pbr_with_tex = pbr_with_tex
        p._prev_mode = None
        if hasattr(p, '_mesh_actor'):
            last_tex = getattr(p, '_last_preloaded_tex', None)
            if last_tex is not None:
                p._mesh_actor.SetTexture(last_tex)
                p._mesh_actor.Modified()
        apply_lighting(p)

    def apply_smooth_cycle(idx):
        if idx == 0:
            _enter_tex_base(is_lighting=False, pbr_with_tex=False)
        elif idx == 1:
            p._is_smooth = True
            p._is_lighting = True
            p._is_tex = False
            p._pbr_with_tex = False
            p._prev_mode = None
            apply_lighting(p)
        else:
            _enter_tex_base(is_lighting=True, pbr_with_tex=True)
        enable_hdri(p)

    def _toggle_smooth():
        was_on = p._is_smooth
        apply_default_reset(p)
        if not was_on:
            p._smooth_cycle = 0
            apply_smooth_cycle(p._smooth_cycle)
        label = (
            SMOOTH_CYCLE_LABELS[p._smooth_cycle]
            if p._is_smooth else ''
        )
        set_mode(label)
        logger.info('Mode: %s', label or 'DEFAULT')
        trigger()

    def _toggle_smooth_shading():
        p._is_smooth_shading = not getattr(
            p, '_is_smooth_shading', False
        )
        p._prev_mode = None
        label = LBL_SURF_SMOOTHING if p._is_smooth_shading else ''
        set_mode(label)
        logger.info('Mode: %s', label or 'DEFAULT')
        trigger()

    bind_key(p, KEY_SMOOTH, _toggle_smooth)
    bind_key(p, KEY_SMOOTH_SHADING, _toggle_smooth_shading)

    p._apply_smooth_cycle = apply_smooth_cycle
    return apply_smooth_cycle
