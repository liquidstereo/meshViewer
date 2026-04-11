import logging
import numpy as np

from configs.defaults import (
    COLOR_BG, ISOLINE_CONTOUR_MAX_FACES, ISO_NORMAL_OFFSET,
)
from process.mode.common import (
    _hex_to_rgb, _set_mesh_input,
    _set_flat_line_lighting, _set_actor_transform, _setup_occluder_actor,
    _get_cam_dir,
)

logger = logging.getLogger(__name__)

_CAM_DIR_TOL = 1e-4

def _get_iso_display(p, mesh):
    if getattr(p, '_cached_iso_display_src', None) is mesh:
        return p._cached_iso_display

    p._cached_iso_count = -1
    p._cached_iso_axis = -1
    p._cached_iso_cam_dir = None

    display = mesh.copy()
    n_faces = display.n_faces_strict
    if n_faces > ISOLINE_CONTOUR_MAX_FACES:
        ratio = max(0.0, 1.0 - ISOLINE_CONTOUR_MAX_FACES / n_faces)
        if not display.is_all_triangles:
            display = display.triangulate()
        display = display.decimate(ratio)
        logger.debug(
            'Isoline display decimated: %d -> %d faces (ratio=%.3f)',
            n_faces, display.n_faces_strict, ratio,
        )

    p._cached_iso_display = display
    p._cached_iso_display_src = mesh
    return display

def apply_isoline(p, mesh):
    iso_count = p._iso_count
    iso_axis = p._iso_axis

    display = _get_iso_display(p, mesh)

    prev_count = getattr(p, '_cached_iso_count', -1)
    prev_axis = getattr(p, '_cached_iso_axis', -1)
    prev_cam_dir = getattr(p, '_cached_iso_cam_dir', None)

    if iso_axis == 3:
        cam_dir = _get_cam_dir(p)
        same_cam = (
            prev_cam_dir is not None
            and np.linalg.norm(cam_dir - prev_cam_dir) < _CAM_DIR_TOL
        )
    else:
        cam_dir = None
        same_cam = True

    need_contour = (
        prev_count != iso_count
        or prev_axis != iso_axis
        or not same_cam
    )

    if not need_contour:
        _set_flat_line_lighting(p._iso_actor.GetProperty())
        _set_actor_transform(p._iso_actor, p)
        p._iso_actor.VisibilityOn()
        return

    if iso_axis == 3:

        display['Depth'] = -(display.points @ cam_dir)
    else:
        display['Depth'] = display.points.T[iso_axis]
    display.set_active_scalars('Depth')
    contours = display.contour(isosurfaces=iso_count)

    if ISO_NORMAL_OFFSET > 0 and contours.n_points > 0:
        display_n = display.compute_normals(
            cell_normals=False, point_normals=True,
            progress_bar=False,
        )
        sampled = contours.sample(display_n, progress_bar=False)
        normals = sampled.point_data.get('Normals')
        if normals is not None and normals.shape[0] == contours.n_points:
            contours.points = (
                contours.points + normals * ISO_NORMAL_OFFSET
            )
    p._iso_mapper.SetInputData(contours)

    lut = getattr(p, '_iso_lut', None)
    if lut is not None:
        if iso_axis == 3:
            depths = display['Depth']
            s_min = float(depths.min())
            s_max = float(depths.max())
        else:
            b = mesh.bounds
            ax = iso_axis
            s_min, s_max = b[ax * 2], b[ax * 2 + 1]
        p._iso_mapper.ScalarVisibilityOn()
        p._iso_mapper.SetLookupTable(lut)
        p._iso_mapper.SetScalarRange(s_min, s_max)
        p._cmap_lut = lut
        p._cmap_range = (s_min, s_max)
        p._cmap_title = 'ISO'
    else:
        p._iso_mapper.ScalarVisibilityOff()

    _set_flat_line_lighting(p._iso_actor.GetProperty())
    _set_actor_transform(p._iso_actor, p)
    p._iso_actor.VisibilityOn()

    p._cached_iso_count = iso_count
    p._cached_iso_axis = iso_axis
    p._cached_iso_cam_dir = cam_dir

def apply_iso_occluder(p, mesh):
    if not getattr(p, '_is_backface', True):
        p._mesh_actor.VisibilityOff()
        p._prev_mode = 'iso_occluder'
        return
    _setup_occluder_actor(p, mesh, polygon_offset=True)
    p._prev_mode = 'iso_occluder'

def apply_iso_only(p, mesh):
    mapper = p._mesh_mapper
    actor = p._mesh_actor

    actor.SetColor(*_hex_to_rgb(COLOR_BG))

    _set_mesh_input(mapper, mesh, p, '_cached_mesh_poly')
    mapper.ScalarVisibilityOff()
    actor.SetTexture(None)

    prop = actor.GetProperty()
    prop.SetOpacity(1.0)
    prop.SetColor(*_hex_to_rgb(COLOR_BG))
    prop.SetLighting(False)
    prop.EdgeVisibilityOff()
    prop.SetRepresentationToSurface()

    p._prev_mode = 'iso_only'
