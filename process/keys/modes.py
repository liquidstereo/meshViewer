import logging

from configs.keybinding import (
    KEY_ISO, KEY_WIRE, KEY_LIGHT, KEY_NORMAL_COLOR,
    KEY_MESH_QUALITY, KEY_VTX, KEY_BACKFACE,
    KEY_FACE_NORMAL, KEY_DEPTH, KEY_EDGE,
)
from configs.settings import (
    PT_CLOUD_SIZE_DEFAULT,
    PT_CLOUD_SIZE_POINT_WHITE,
    PT_CLOUD_SIZE_DEPTH,
)
from process.mode.default import apply_default_reset
from process.mode.labels import (
    LBL_ISOLINE, LBL_WIREFRAME, LBL_REDUCTION,
    LBL_SURF_NORMAL, LBL_QUALITY, LBL_VERTICES,
    LBL_FACE_NORMAL, LBL_DEPTH, LBL_EDGE,
    LBL_MESH_HIDDEN, LBL_MESH_VISIBLE,
    LBL_BFC_ON, LBL_BFC_OFF,
    LBL_PT_CLOUD_RGB, LBL_PT_CLOUD_WHITE, LBL_PT_CLOUD_DEPTH,
    LBL_PT_FOG_ON, LBL_PT_FOG_OFF,
)
from process.scene.lighting import apply_lighting
from process.keys import bind_key

logger = logging.getLogger(__name__)

def register(p, trigger, set_mode):
    def _toggle_iso():
        was_on = p._is_isoline
        apply_default_reset(p)
        if not was_on:
            p._is_isoline = True
            p._is_backface = False
        label = LBL_ISOLINE if p._is_isoline else ''
        set_mode(label)
        logger.info('Mode: %s', label or 'DEFAULT')
        trigger()

    def _toggle_wire():
        was_on = p._is_wire
        apply_default_reset(p)
        if not was_on:
            p._is_wire = True
            p._wire_mesh_hidden = True
        else:
            if hasattr(p, '_mesh_actor'):
                p._mesh_actor.VisibilityOn()
        label = LBL_WIREFRAME if p._is_wire else ''
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
        label = LBL_REDUCTION if p._is_lighting else ''
        set_mode(label)
        logger.info('Mode: %s', label or 'DEFAULT')
        trigger()

    def _toggle_normal_color():
        was_on = p._is_normal_color
        apply_default_reset(p)
        if not was_on:
            p._is_normal_color = True
        label = LBL_SURF_NORMAL if p._is_normal_color else ''
        set_mode(label)
        logger.info('Mode: %s', label or 'DEFAULT')
        trigger()

    def _toggle_mesh_quality():
        was_on = p._is_mesh_quality
        apply_default_reset(p)
        if not was_on:
            p._is_mesh_quality = True
        label = LBL_QUALITY if p._is_mesh_quality else ''
        set_mode(label)
        logger.info('Mode: %s', label or 'DEFAULT')
        trigger()

    def _toggle_vtx():

        if getattr(p, '_n_faces', 1) == 0:
            apply_default_reset(p)
            p._prev_mode = None
            p._pt_cloud_depth = False
            p._pt_cloud_use_rgb = not getattr(p, '_pt_cloud_use_rgb', False)
            if p._pt_cloud_use_rgb:
                p._pt_cloud_size = PT_CLOUD_SIZE_DEFAULT
                label = LBL_PT_CLOUD_RGB
            elif getattr(p, '_pt_cloud_depth', False):
                label = LBL_PT_CLOUD_DEPTH
            else:
                p._pt_cloud_size = PT_CLOUD_SIZE_POINT_WHITE
                label = LBL_PT_CLOUD_WHITE
            set_mode(label)
            logger.info('Mode: %s', label)
            trigger()
            return

        was_on = p._is_vtx
        apply_default_reset(p)
        if not was_on:
            p._is_vtx = True
            p._vtx_mesh_hidden = False
        label = LBL_VERTICES if p._is_vtx else ''
        set_mode(label)
        logger.info('Mode: %s', label or 'DEFAULT')
        trigger()

    def _toggle_face_normal():
        was_on = p._is_fnormal
        apply_default_reset(p)
        if not was_on:
            p._is_fnormal = True
            p._fnormal_mesh_hidden = False
        else:
            if hasattr(p, '_mesh_actor'):
                p._mesh_actor.VisibilityOn()
        label = LBL_FACE_NORMAL if p._is_fnormal else ''
        set_mode(label)
        logger.info('Mode: %s', label or 'DEFAULT')
        trigger()

    def _toggle_depth():
        was_on = p._is_depth
        apply_default_reset(p)
        if not was_on:
            p._is_depth = True
            if getattr(p, '_n_faces', 1) == 0:
                p._pt_cloud_size = PT_CLOUD_SIZE_DEPTH
        else:
            if getattr(p, '_n_faces', 1) == 0:
                p._pt_cloud_size = PT_CLOUD_SIZE_DEFAULT
        label = LBL_DEPTH if p._is_depth else ''
        set_mode(label)
        logger.info('Mode: %s', label or 'DEFAULT')
        trigger()

    def _toggle_edge():
        was_on = getattr(p, '_is_edge', False)
        apply_default_reset(p)
        if not was_on:
            p._is_edge = True
            p._edge_mesh_hidden = False
        else:
            if hasattr(p, '_mesh_actor'):
                p._mesh_actor.VisibilityOn()
        label = LBL_EDGE if p._is_edge else ''
        set_mode(label)
        logger.info('Mode: %s', label or 'DEFAULT')
        trigger()

    def _toggle_backface():
        if getattr(p, '_n_faces', 1) == 0:
            p._pt_fog_enabled = not getattr(p, '_pt_fog_enabled', False)
            p._pt_fog_cache_key = None
            p._pt_normal_color_key = None
            p._prev_mode = None
            if not p._pt_fog_enabled and (
                getattr(p, '_pt_fog_gpu', None)
                or getattr(p, '_depth_fog_gpu', None)
            ):
                try:
                    sp = p._mesh_actor.GetShaderProperty()
                    sp.ClearAllVertexShaderReplacements()
                    sp.SetFragmentShaderCode('')
                except AttributeError:
                    pass
                p._pt_fog_gpu = None
                p._pt_fog_unif_key = None
                p._pt_fog_color_key = None
                p._depth_fog_gpu = None
                p._depth_unif_key = None
                p._depth_scalar_key = None
                p._pt_shader_size = -1
            label = LBL_PT_FOG_ON if p._pt_fog_enabled else LBL_PT_FOG_OFF
            set_mode(label)
            logger.info('Mode: %s', label)
            trigger()
            return
        if getattr(p, '_is_wire', False):
            p._wire_mesh_hidden = not getattr(
                p, '_wire_mesh_hidden', False
            )
            if hasattr(p, '_mesh_actor'):
                if p._wire_mesh_hidden:
                    p._mesh_actor.VisibilityOff()
                else:
                    p._mesh_actor.VisibilityOn()
            label = (
                LBL_MESH_HIDDEN
                if p._wire_mesh_hidden
                else LBL_MESH_VISIBLE
            )
        elif getattr(p, '_is_vtx', False):
            p._vtx_mesh_hidden = not getattr(
                p, '_vtx_mesh_hidden', False
            )
            if hasattr(p, '_mesh_actor'):
                if p._vtx_mesh_hidden:
                    p._mesh_actor.VisibilityOff()
                else:
                    p._mesh_actor.VisibilityOn()
            label = (
                LBL_MESH_HIDDEN
                if p._vtx_mesh_hidden
                else LBL_MESH_VISIBLE
            )
        elif getattr(p, '_is_edge', False):
            p._edge_mesh_hidden = not getattr(
                p, '_edge_mesh_hidden', True
            )
            if hasattr(p, '_mesh_actor'):
                if p._edge_mesh_hidden:
                    p._mesh_actor.VisibilityOff()
                else:
                    p._mesh_actor.VisibilityOn()
            label = (
                LBL_EDGE_HIDDEN
                if p._edge_mesh_hidden
                else LBL_EDGE_VISIBLE
            )
        elif getattr(p, '_is_fnormal', False):
            p._fnormal_mesh_hidden = not getattr(
                p, '_fnormal_mesh_hidden', True
            )
            if hasattr(p, '_mesh_actor'):
                if p._fnormal_mesh_hidden:
                    p._mesh_actor.VisibilityOff()
                else:
                    p._mesh_actor.VisibilityOn()
            label = (
                LBL_MESH_HIDDEN
                if p._fnormal_mesh_hidden
                else LBL_MESH_VISIBLE
            )
        else:
            p._is_backface = not p._is_backface
            label = (
                LBL_BFC_ON
                if p._is_backface
                else LBL_BFC_OFF
            )
        set_mode(label)
        logger.info('Mode: %s', label)
        trigger()

    bind_key(p, KEY_ISO, _toggle_iso)
    bind_key(p, KEY_WIRE, _toggle_wire)
    bind_key(p, KEY_LIGHT, _toggle_light)
    bind_key(p, KEY_NORMAL_COLOR, _toggle_normal_color)
    bind_key(p, KEY_MESH_QUALITY, _toggle_mesh_quality)
    bind_key(p, KEY_VTX, _toggle_vtx)
    bind_key(p, KEY_FACE_NORMAL, _toggle_face_normal)
    bind_key(p, KEY_DEPTH, _toggle_depth)
    bind_key(p, KEY_EDGE, _toggle_edge)
    bind_key(p, KEY_BACKFACE, _toggle_backface)
