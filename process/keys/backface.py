import logging

from configs.keybinding import KEY_BACKFACE
from process.mode.labels import (
    LBL_MESH_HIDDEN, LBL_MESH_VISIBLE,
    LBL_EDGE_HIDDEN, LBL_EDGE_VISIBLE,
    LBL_BFC_ON, LBL_BFC_OFF,
    LBL_PT_FOG_ON, LBL_PT_FOG_OFF,
)
from process.keys import bind_key

logger = logging.getLogger(__name__)

_MESH_HIDE_MODES = (
    ('_is_wire', '_wire_mesh_hidden', True,
     LBL_MESH_HIDDEN, LBL_MESH_VISIBLE),
    ('_is_vtx', '_vtx_mesh_hidden', False,
     LBL_MESH_HIDDEN, LBL_MESH_VISIBLE),
    ('_is_edge', '_edge_mesh_hidden', False,
     LBL_EDGE_HIDDEN, LBL_EDGE_VISIBLE),
    ('_is_outline', '_outline_mesh_hidden', True,
     LBL_MESH_HIDDEN, LBL_MESH_VISIBLE),
    ('_is_fnormal', '_fnormal_mesh_hidden', True,
     LBL_MESH_HIDDEN, LBL_MESH_VISIBLE),
)

def _clear_pt_shaders(p) -> None:
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

def toggle_pt_fog(p) -> str:
    p._pt_fog_enabled = not getattr(p, '_pt_fog_enabled', False)
    p._pt_fog_cache_key = None
    p._pt_normal_color_key = None
    p._prev_mode = None
    if not p._pt_fog_enabled and (
        getattr(p, '_pt_fog_gpu', None)
        or getattr(p, '_depth_fog_gpu', None)
    ):
        _clear_pt_shaders(p)
    return LBL_PT_FOG_ON if p._pt_fog_enabled else LBL_PT_FOG_OFF

def toggle_mesh_hidden(p) -> str | None:
    for flag, hide_attr, default, hidden_lbl, visible_lbl in (
        _MESH_HIDE_MODES
    ):
        if not getattr(p, flag, False):
            continue
        hidden = not getattr(p, hide_attr, default)
        setattr(p, hide_attr, hidden)
        if hasattr(p, '_mesh_actor'):
            if hidden:
                p._mesh_actor.VisibilityOff()
            else:
                p._mesh_actor.VisibilityOn()
        return hidden_lbl if hidden else visible_lbl
    return None

def toggle_backface_culling(p) -> str:
    p._is_backface = not p._is_backface
    return LBL_BFC_ON if p._is_backface else LBL_BFC_OFF

def register(p, trigger, set_mode) -> None:
    def _toggle_backface():
        if getattr(p, '_n_faces', 1) == 0:
            label = toggle_pt_fog(p)
        else:
            label = toggle_mesh_hidden(p) or toggle_backface_culling(p)
        set_mode(label)
        logger.info('Mode: %s', label)
        trigger()

    bind_key(p, KEY_BACKFACE, _toggle_backface)
