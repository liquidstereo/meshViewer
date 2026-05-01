from configs.settings import (
    ISO_COUNT_STEP, REDUCTION_MESH_STEP, EDGE_FEATURE_ANGLE_STEP,
    HDRI_ROT_STEP, VTX_SPATIAL_INTERVAL, VTX_SPATIAL_STEP,
    PT_CLOUD_SIZE_STEP, PT_CLOUD_SIZE_MIN, PT_CLOUD_SIZE_MAX,
    NP_CLOUD_SIZE_STEP, NP_CLOUD_SIZE_MIN, NP_CLOUD_SIZE_MAX,
)
from configs.keybinding import (
    KEY_INC, KEY_DEC, KEY_AXIS_NEXT, KEY_AXIS_PREV,
)
from process.mode.labels import (
    SMOOTH_CYCLE_LABELS, AXIS_NAMES,
    FMT_HDRI_ROT, FMT_EDGE_ANGLE, FMT_ISO_COUNT,
    FMT_VTX_INTERVAL, FMT_MESH_RED, FMT_PT_SIZE,
    FMT_ISO_AXIS, FMT_DEPTH_AXIS, FMT_WIRE_AXIS, FMT_NORMAL_AXIS,

)
from process.scene.hdri import rotate_hdri
from process.keys import bind_key, dispatch_key
import logging
logger = logging.getLogger(__name__)

def register(p, trigger, set_mode, apply_smooth_cycle):
    def _rotate_hdri(delta):
        p._hdri_rotation = (
            getattr(p, '_hdri_rotation', 0.0) + delta
        ) % 360.0
        rotate_hdri(p, p._hdri_rotation)
        set_mode(FMT_HDRI_ROT.format(p._hdri_rotation))
        trigger()

    def _is_pbr_mode():

        return getattr(p, '_is_smooth', False)

    def _increment():
        if _is_pbr_mode():
            _rotate_hdri(HDRI_ROT_STEP)
        elif getattr(p, '_is_edge', False):
            p._edge_feature_angle = round(
                min(180.0,
                    p._edge_feature_angle + EDGE_FEATURE_ANGLE_STEP),
                1,
            )
            set_mode(FMT_EDGE_ANGLE.format(p._edge_feature_angle))
            trigger()
        elif p._is_isoline:
            p._iso_count = min(100, p._iso_count + ISO_COUNT_STEP)
            set_mode(FMT_ISO_COUNT.format(p._iso_count))
            trigger()
        elif getattr(p, '_is_vtx', False):
            p._vtx_spatial_interval = round(
                p._vtx_spatial_interval + VTX_SPATIAL_STEP, 4
            )
            set_mode(FMT_VTX_INTERVAL.format(p._vtx_spatial_interval))
            trigger()
        elif getattr(p, '_n_faces', 1) == 0:
            _is_np = getattr(p, '_is_np_data', False)
            _sz_max = NP_CLOUD_SIZE_MAX if _is_np else PT_CLOUD_SIZE_MAX
            _sz_step = NP_CLOUD_SIZE_STEP if _is_np else PT_CLOUD_SIZE_STEP
            p._pt_cloud_size = min(
                _sz_max,
                p._pt_cloud_size + _sz_step,
            )
            actor = getattr(p, '_mesh_actor', None)
            if actor is not None:
                actor.GetProperty().SetPointSize(p._pt_cloud_size)
            set_mode(FMT_PT_SIZE.format(p._pt_cloud_size))
            trigger()
        else:
            p._reduction_mesh = round(
                min(1.0, p._reduction_mesh + REDUCTION_MESH_STEP), 2
            )
            set_mode(FMT_MESH_RED.format(p._reduction_mesh))
            trigger()

    def _decrement():
        if _is_pbr_mode():
            _rotate_hdri(-HDRI_ROT_STEP)
        elif getattr(p, '_is_edge', False):
            p._edge_feature_angle = round(
                max(1.0,
                    p._edge_feature_angle - EDGE_FEATURE_ANGLE_STEP),
                1,
            )
            set_mode(FMT_EDGE_ANGLE.format(p._edge_feature_angle))
            trigger()
        elif p._is_isoline:
            p._iso_count = max(5, p._iso_count - ISO_COUNT_STEP)
            set_mode(FMT_ISO_COUNT.format(p._iso_count))
            trigger()
        elif getattr(p, '_is_vtx', False):
            p._vtx_spatial_interval = round(
                max(VTX_SPATIAL_STEP,
                    p._vtx_spatial_interval - VTX_SPATIAL_STEP),
                4,
            )
            set_mode(FMT_VTX_INTERVAL.format(p._vtx_spatial_interval))
            trigger()
        elif getattr(p, '_n_faces', 1) == 0:
            _is_np = getattr(p, '_is_np_data', False)
            _sz_min = NP_CLOUD_SIZE_MIN if _is_np else PT_CLOUD_SIZE_MIN
            _sz_step = NP_CLOUD_SIZE_STEP if _is_np else PT_CLOUD_SIZE_STEP
            p._pt_cloud_size = max(
                _sz_min,
                p._pt_cloud_size - _sz_step,
            )
            actor = getattr(p, '_mesh_actor', None)
            if actor is not None:
                actor.GetProperty().SetPointSize(p._pt_cloud_size)
            set_mode(FMT_PT_SIZE.format(p._pt_cloud_size))
            trigger()
        else:
            p._reduction_mesh = round(
                max(0.1, p._reduction_mesh - REDUCTION_MESH_STEP), 2
            )
            set_mode(FMT_MESH_RED.format(p._reduction_mesh))
            trigger()

    def _has_axis_mode():
        return (
            p._is_isoline
            or getattr(p, '_is_depth', False)
            or getattr(p, '_is_wire', False)
            or getattr(p, '_is_fnormal', False)
        )

    def _cycle_axis(delta):
        if p._is_isoline:
            p._iso_axis = (p._iso_axis + delta) % 4
            set_mode(FMT_ISO_AXIS.format(AXIS_NAMES[p._iso_axis]))
            trigger()
        elif getattr(p, '_is_depth', False):
            p._depth_axis = (
                getattr(p, '_depth_axis', 3) + delta
            ) % 4
            set_mode(FMT_DEPTH_AXIS.format(AXIS_NAMES[p._depth_axis]))
            trigger()
        elif getattr(p, '_is_wire', False):
            p._wire_axis = (
                getattr(p, '_wire_axis', 3) + delta
            ) % 4
            set_mode(FMT_WIRE_AXIS.format(AXIS_NAMES[p._wire_axis]))
            trigger()
        elif getattr(p, '_is_fnormal', False):
            p._fnormal_axis = (
                getattr(p, '_fnormal_axis', 3) + delta
            ) % 4
            set_mode(FMT_NORMAL_AXIS.format(AXIS_NAMES[p._fnormal_axis]))
            trigger()

    def _cycle_smooth(step):
        p._smooth_cycle = (p._smooth_cycle + step) % 3
        apply_smooth_cycle(p._smooth_cycle)
        set_mode(SMOOTH_CYCLE_LABELS[p._smooth_cycle])
        trigger()

    def _axis_next():
        if _has_axis_mode():
            _cycle_axis(1)
        elif getattr(p, '_is_smooth', False):
            _cycle_smooth(1)

    def _axis_prev():
        if _has_axis_mode():
            _cycle_axis(-1)
        elif getattr(p, '_is_smooth', False):
            _cycle_smooth(-1)

    bind_key(p, KEY_INC, _increment)
    bind_key(p, KEY_DEC, _decrement)
    dispatch_key(p._special_key_dispatch, KEY_AXIS_NEXT, _axis_next)
    dispatch_key(p._special_key_dispatch, KEY_AXIS_PREV, _axis_prev)
