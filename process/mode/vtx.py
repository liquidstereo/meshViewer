import logging
import numpy as np
import vtk
from vtk.util.numpy_support import numpy_to_vtk
import configs.settings as _cfg

from configs.settings import (
    VTX_SPATIAL_INTERVAL, VTX_SCREEN_INTERVAL,
    VTX_LABEL_COLOR,
)
from process.mode.common import _project_to_screen, _hex_to_rgb

logger = logging.getLogger(__name__)

_HASH_OFFSET = 1 << 20
_HASH_SHIFT1 = 21
_HASH_SHIFT2 = 42

def _hide_vtx(p) -> None:
    p._vtx_world_pts = None
    p._vtx_indices = None
    p._vtx_label_actor.VisibilityOff()
    for ta in getattr(p, '_vtx_text_actors', []):
        ta.VisibilityOff()
    p._vtx_point_actor.VisibilityOff()

def apply_vtx_labels(p, mesh):
    cam = p.renderer.GetActiveCamera()
    cam_state = (
        cam.GetDirectionOfProjection(),
        cam.GetPosition(),
        cam.GetParallelScale(),
    )
    if (getattr(p, '_cached_vtx_src', None) is mesh
            and getattr(p, '_cached_vtx_cam', None) == cam_state):
        pool = getattr(p, '_vtx_text_actors', [])
        n = getattr(p, '_vtx_active_count', 0)
        for ta in pool[:n]:
            ta.VisibilityOn()
        p._vtx_point_actor.VisibilityOn()
        return

    s = getattr(p, '_norm_scale', 1.0)
    c = np.array(getattr(p, '_norm_center', [0.0, 0.0, 0.0]))
    world_pts = s * mesh.points + (1.0 - s) * c
    n_pts = len(world_pts)

    spatial_interval = getattr(p, '_vtx_spatial_interval', VTX_SPATIAL_INTERVAL)
    if spatial_interval > 0.0:
        w_cells = np.floor(
            world_pts / spatial_interval
        ).astype(np.int64)
        w_hash = (
            (w_cells[:, 0] + _HASH_OFFSET)
            + (w_cells[:, 1] + _HASH_OFFSET) * (1 << _HASH_SHIFT1)
            + (w_cells[:, 2] + _HASH_OFFSET) * (1 << _HASH_SHIFT2)
        )
        _, w_first = np.unique(w_hash, return_index=True)
        cand_idx = np.sort(w_first).astype(np.int32)
    else:
        cand_idx = np.arange(n_pts, dtype=np.int32)

    if len(cand_idx) == 0:
        _hide_vtx(p)
        return

    if 'Normals' not in mesh.point_data:

        mesh.compute_normals(inplace=True, split_vertices=False)
    normals = mesh.point_data['Normals']
    cam_dir = np.array(
        p.renderer.GetActiveCamera().GetDirectionOfProjection(),
        dtype=np.float64,
    )
    front = (normals[cand_idx].astype(np.float64) @ cam_dir) < 0.0
    cand_idx = cand_idx[front]

    if len(cand_idx) == 0:
        _hide_vtx(p)
        return

    cand_world = world_pts[cand_idx]
    screen, visible = _project_to_screen(p, cand_world)
    cand_idx = cand_idx[visible]
    screen = screen[visible]

    if len(cand_idx) == 0:
        _hide_vtx(p)
        return

    scr_cells = np.floor(screen / VTX_SCREEN_INTERVAL).astype(np.int64)
    scr_hash = scr_cells[:, 0] + scr_cells[:, 1] * (1 << _HASH_SHIFT1)
    _, first_occ = np.unique(scr_hash, return_index=True)
    sorted_occ = np.sort(first_occ)
    indices = cand_idx[sorted_occ]
    selected_world = world_pts[indices]

    selected_screen = screen[sorted_occ]

    p._vtx_world_pts = selected_world
    p._vtx_indices = indices

    vtk_world_data = numpy_to_vtk(selected_world, deep=True)
    pt_poly = getattr(p, '_vtx_poly', None)
    if pt_poly is None:
        p._vtx_poly = vtk.vtkPolyData()
        pt_poly = p._vtx_poly
        pt_poly.SetPoints(vtk.vtkPoints())

    pt_poly.GetPoints().SetData(vtk_world_data)
    pt_poly.GetPoints().Modified()
    pt_poly.Modified()

    p._vtx_glyph.SetInputData(pt_poly)
    p._vtx_glyph.Update()
    p._vtx_point_actor.VisibilityOn()

    n = len(indices)
    pool = getattr(p, '_vtx_text_actors', [])
    while len(pool) < n:
        ta = vtk.vtkTextActor()
        tp = ta.GetTextProperty()
        tp.SetFontFamilyToCourier()
        tp.SetFontSize(_cfg.VTX_LABEL_FONT_SIZE)
        tp.SetColor(*_hex_to_rgb(VTX_LABEL_COLOR))
        tp.BoldOff()
        tp.ShadowOff()
        tp.ItalicOff()
        ta.GetPositionCoordinate().SetCoordinateSystemToDisplay()
        ta.VisibilityOff()
        p.renderer.AddActor2D(ta)
        pool.append(ta)
    p._vtx_text_actors = pool
    p._vtx_active_count = n
    for i in range(n):
        pool[i].SetInput(str(int(indices[i])))
        pool[i].SetPosition(
            float(selected_screen[i, 0]),
            float(selected_screen[i, 1]),
        )
        pool[i].VisibilityOn()
    for i in range(n, len(pool)):
        pool[i].VisibilityOff()
    p._vtx_label_actor.VisibilityOff()

    p._cached_vtx_src = mesh
    p._cached_vtx_cam = cam_state

def apply_vtx_pick(plotter, click_x: int, click_y: int) -> None:
    world_pts = getattr(plotter, '_vtx_world_pts', None)
    indices = getattr(plotter, '_vtx_indices', None)
    if world_pts is None or indices is None or len(indices) == 0:
        return

    screen, _ = _project_to_screen(plotter, world_pts)
    dists = (
        (screen[:, 0] - click_x) ** 2
        + (screen[:, 1] - click_y) ** 2
    )
    nearest = int(np.argmin(dists))
    vtx_idx = int(indices[nearest])
    world_pt = world_pts[nearest]

    plotter._vtx_pick_pts.SetPoint(0, *world_pt)
    plotter._vtx_pick_pts.Modified()
    plotter._vtx_pick_poly.Modified()
    plotter._vtx_sel_actor.VisibilityOn()

    x, y, z = world_pt
    plotter._vtx_pick_text.SetInput(
        f'VTX {vtx_idx}   ({x:.4f}, {y:.4f}, {z:.4f})'
    )
    plotter._vtx_pick_text.VisibilityOn()
    logger.debug(
        'Vertex picked: idx=%d pos=(%.4f, %.4f, %.4f)',
        vtx_idx, x, y, z,
    )
