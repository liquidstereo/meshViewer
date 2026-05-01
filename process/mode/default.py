import logging

from configs.settings import (
    SHOW_BACKFACE, REDUCTION_MESH,
    RENDER_MSAA_SAMPLES, SAVE_ALPHA,
)
from process.scene.lighting import apply_lighting
from process.scene.hdri import disable_hdri
from process.mode.vtx import _hide_vtx

logger = logging.getLogger(__name__)

def apply_default_reset(p) -> None:
    p._is_audio = False
    p._audio_renderer = None
    p._is_isoline = False
    p._is_iso_only = False
    p._is_wire = False
    p._wire_mesh_hidden = False
    p._is_normal_color = False
    p._is_mesh_quality = False
    p._is_depth = False
    p._is_edge = False
    p._edge_mesh_hidden = False
    p._is_vtx = False
    if hasattr(p, '_vtx_label_actor'):
        _hide_vtx(p)
    p._is_fnormal = False
    p._is_smooth = False
    p._smooth_cycle = 0
    p._pbr_with_tex = False
    p._prev_pbr_tex = None
    p._is_tex = False
    p._is_backface = SHOW_BACKFACE
    p._reduction_mesh = REDUCTION_MESH
    p._prev_mode = None

    p._is_lighting = False
    apply_lighting(p)

    if hasattr(p, '_mesh_actor'):
        p._mesh_actor.SetTexture(None)
        prop = p._mesh_actor.GetProperty()
        prop.SetTexture('albedoTex', None)
        prop.SetInterpolationToFlat()
        prop.SetSpecular(0.0)
        prop.SetMetallic(0.0)
        prop.SetRoughness(0.5)
        try:
            sp = p._mesh_actor.GetShaderProperty()
            sp.ClearAllVertexShaderReplacements()
            sp.SetFragmentShaderCode('')
        except AttributeError:
            pass

    if hasattr(p, '_mesh_mapper'):
        p._mesh_mapper.SetResolveCoincidentTopologyToOff()

    p._pt_fog_cache_key = None
    p._pt_depth_cache_key = None
    p._pt_normal_color_key = None
    p._pt_shader_size = -1
    p._pt_fog_gpu = None
    p._pt_fog_gpu_base = -1
    p._pt_fog_unif_key = None
    p._pt_fog_color_key = None

    p._depth_fog_gpu = None
    p._depth_fog_gpu_base = -1
    p._depth_fog_gpu_fog = None
    p._depth_unif_key = None
    p._depth_scalar_key = None
    p._pt_size_unif_key = None

    disable_hdri(p)

    if not SAVE_ALPHA and hasattr(p, 'render_window'):
        rw = p.render_window
        if rw.GetMultiSamples() != RENDER_MSAA_SAMPLES:
            rw.SetMultiSamples(RENDER_MSAA_SAMPLES)
            logger.debug(
                'apply_default_reset: MSAA restored to %d',
                RENDER_MSAA_SAMPLES,
            )

    logger.debug('apply_default_reset: done')
