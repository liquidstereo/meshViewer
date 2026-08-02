import logging

from configs.keybinding import (
    KEY_ISO, KEY_WIRE, KEY_LIGHT, KEY_NORMAL_COLOR,
    KEY_MESH_QUALITY, KEY_VTX,
    KEY_FACE_NORMAL, KEY_DEPTH, KEY_EDGE, KEY_ID, KEY_OUTLINE,
)
from configs.settings import (
    PT_CLOUD_SIZE_DEFAULT,
    PT_CLOUD_SIZE_POINT_WHITE,
    PT_CLOUD_SIZE_DEPTH,
    NP_CLOUD_SIZE_DEFAULT,
    NP_CLOUD_SIZE_POINT_WHITE,
    NP_CLOUD_SIZE_DEPTH,
)
from process.mode.default import apply_default_reset
from process.mode.labels import (
    LBL_ISOLINE, LBL_WIREFRAME, LBL_REDUCTION,
    LBL_QUALITY, LBL_VERTICES, normal_light_label,
    LBL_FACE_NORMAL, LBL_DEPTH, LBL_EDGE, LBL_OUTLINE,
    LBL_PT_CLOUD_RGB, LBL_PT_CLOUD_WHITE, LBL_PT_CLOUD_DEPTH,
    id_style_label,
)
from process.scene.lighting import apply_lighting
from process.plotter.state import (
    restore_startup_mode, apply_mode_entry_state,
)
from process.keys import bind_key

logger = logging.getLogger(__name__)

def register(p, trigger, set_mode):
    def _toggle_iso():
        was_on = p._is_isoline
        apply_default_reset(p)
        if not was_on:
            p._is_isoline = True
            apply_mode_entry_state(p, 'isoline')
            label = LBL_ISOLINE
        else:
            label = restore_startup_mode(p)
        set_mode(label)
        logger.info('Mode: %s', label or 'DEFAULT')
        trigger()

    def _toggle_wire():
        was_on = p._is_wire
        apply_default_reset(p)
        if not was_on:
            p._is_wire = True
            apply_mode_entry_state(p, 'wire')
            label = LBL_WIREFRAME
        else:
            if hasattr(p, '_mesh_actor'):
                p._mesh_actor.VisibilityOn()
            label = restore_startup_mode(p)
        set_mode(label)
        logger.info('Mode: %s', label or 'DEFAULT')
        trigger()

    def _toggle_light():
        was_on = p._is_lighting
        apply_default_reset(p)
        if not was_on:
            p._is_lighting = True
            apply_lighting(p)
            p._reduction_mesh = 0.1
            label = LBL_REDUCTION
        else:
            label = restore_startup_mode(p)
        set_mode(label)
        logger.info('Mode: %s', label or 'DEFAULT')
        trigger()

    def _toggle_normal_color():
        was_on = p._is_normal_color
        apply_default_reset(p)
        if not was_on:
            p._is_normal_color = True
            label = normal_light_label(
                getattr(p, '_normal_color_lighting', False)
            )
        else:
            label = restore_startup_mode(p)
        set_mode(label)
        logger.info('Mode: %s', label or 'DEFAULT')
        trigger()

    def _toggle_mesh_quality():
        was_on = p._is_mesh_quality
        apply_default_reset(p)
        if not was_on:
            p._is_mesh_quality = True
            label = LBL_QUALITY
        else:
            label = restore_startup_mode(p)
        set_mode(label)
        logger.info('Mode: %s', label or 'DEFAULT')
        trigger()

    def _toggle_vtx():

        if getattr(p, '_n_faces', 1) == 0:
            _is_np = getattr(p, '_is_np_data', False)
            _sz_rgb = NP_CLOUD_SIZE_DEFAULT if _is_np else PT_CLOUD_SIZE_DEFAULT
            _sz_white = (
                NP_CLOUD_SIZE_POINT_WHITE if _is_np
                else PT_CLOUD_SIZE_POINT_WHITE
            )
            apply_default_reset(p)
            p._prev_mode = None
            p._pt_cloud_depth = False
            p._pt_cloud_use_rgb = not getattr(p, '_pt_cloud_use_rgb', False)
            if p._pt_cloud_use_rgb:
                p._pt_cloud_size = _sz_rgb
                label = LBL_PT_CLOUD_RGB
            elif getattr(p, '_pt_cloud_depth', False):
                label = LBL_PT_CLOUD_DEPTH
            else:
                p._pt_cloud_size = _sz_white
                label = LBL_PT_CLOUD_WHITE
            set_mode(label)
            logger.info('Mode: %s', label)
            trigger()
            return

        was_on = p._is_vtx
        apply_default_reset(p)
        if not was_on:
            p._is_vtx = True
            apply_mode_entry_state(p, 'vtx')
            label = LBL_VERTICES
        else:
            label = restore_startup_mode(p)
        set_mode(label)
        logger.info('Mode: %s', label or 'DEFAULT')
        trigger()

    def _toggle_face_normal():
        was_on = p._is_fnormal
        apply_default_reset(p)
        if not was_on:
            p._is_fnormal = True
            apply_mode_entry_state(p, 'face_normal')
            label = LBL_FACE_NORMAL
        else:
            if hasattr(p, '_mesh_actor'):
                p._mesh_actor.VisibilityOn()
            label = restore_startup_mode(p)
        set_mode(label)
        logger.info('Mode: %s', label or 'DEFAULT')
        trigger()

    def _toggle_depth():
        was_on = p._is_depth
        apply_default_reset(p)
        if not was_on:
            p._is_depth = True
            if getattr(p, '_n_faces', 1) == 0:
                _is_np = getattr(p, '_is_np_data', False)
                p._pt_cloud_size = (
                    NP_CLOUD_SIZE_DEPTH if _is_np else PT_CLOUD_SIZE_DEPTH
                )
            label = LBL_DEPTH
        else:
            if getattr(p, '_n_faces', 1) == 0:
                _is_np = getattr(p, '_is_np_data', False)
                p._pt_cloud_size = (
                    NP_CLOUD_SIZE_DEFAULT if _is_np
                    else PT_CLOUD_SIZE_DEFAULT
                )
            label = restore_startup_mode(p)
        set_mode(label)
        logger.info('Mode: %s', label or 'DEFAULT')
        trigger()

    def _toggle_id():
        was_on = getattr(p, '_is_id', False)
        apply_default_reset(p)
        if not was_on:
            p._is_id = True
            label = id_style_label(getattr(p, '_id_style', 1))
        else:
            label = restore_startup_mode(p)
        set_mode(label)
        logger.info('Mode: %s', label or 'DEFAULT')
        trigger()

    def _toggle_edge():
        was_on = getattr(p, '_is_edge', False)
        apply_default_reset(p)
        if not was_on:
            p._is_edge = True
            apply_mode_entry_state(p, 'edge')
            label = LBL_EDGE
        else:
            if hasattr(p, '_mesh_actor'):
                p._mesh_actor.VisibilityOn()
            label = restore_startup_mode(p)
        set_mode(label)
        logger.info('Mode: %s', label or 'DEFAULT')
        trigger()

    def _toggle_outline():
        was_on = getattr(p, '_is_outline', False)
        apply_default_reset(p)
        if not was_on:
            p._is_outline = True
            apply_mode_entry_state(p, 'outline')
            label = LBL_OUTLINE
        else:
            if hasattr(p, '_mesh_actor'):
                p._mesh_actor.VisibilityOn()
            label = restore_startup_mode(p)
        set_mode(label)
        logger.info('Mode: %s', label or 'DEFAULT')
        trigger()

    bind_key(p, KEY_ISO, _toggle_iso)
    bind_key(p, KEY_WIRE, _toggle_wire)
    bind_key(p, KEY_LIGHT, _toggle_light)
    bind_key(p, KEY_NORMAL_COLOR, _toggle_normal_color)
    bind_key(p, KEY_MESH_QUALITY, _toggle_mesh_quality)
    bind_key(p, KEY_VTX, _toggle_vtx)
    bind_key(p, KEY_FACE_NORMAL, _toggle_face_normal)
    bind_key(p, KEY_DEPTH, _toggle_depth)
    bind_key(p, KEY_ID, _toggle_id)
    bind_key(p, KEY_EDGE, _toggle_edge)
    bind_key(p, KEY_OUTLINE, _toggle_outline)
