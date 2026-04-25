import numpy as np
import vtk
import pyvista as pv
import matplotlib.cm as cm
from vtk.util.numpy_support import numpy_to_vtk

from configs.settings import COLOR_BG, OFFSET_MESH_BACK

def _get_cam_dir(plotter) -> np.ndarray:
    cam_pos = np.array(plotter.camera.position)
    cam_fp = np.array(plotter.camera.focal_point)
    cam_dir = cam_fp - cam_pos
    norm = np.linalg.norm(cam_dir)
    if norm > 0:
        cam_dir /= norm
    return cam_dir

def _hex_to_rgb(hex_color):
    h = hex_color.lstrip('#')
    return tuple(int(h[i:i+2], 16) / 255 for i in (0, 2, 4))

def _set_font_family(prop, family: str) -> None:
    f = family.lower()
    if f == 'arial':
        prop.SetFontFamilyToArial()
    elif f == 'times':
        prop.SetFontFamilyToTimes()
    else:
        prop.SetFontFamilyToCourier()

def _resolve_color(color):
    if color.startswith('#'):
        return _hex_to_rgb(color)
    return cm.get_cmap(color)(0.65)[:3]

def _make_vtk_lut(cmap_name, n=256):
    cmap = cm.get_cmap(cmap_name, n)
    lut = vtk.vtkLookupTable()
    lut.SetNumberOfColors(n)
    lut.Build()
    for i in range(n):
        r, g, b, a = cmap(i / (n - 1))
        lut.SetTableValue(i, r, g, b, a)
    return lut

def _project_to_screen(p, world_pts: np.ndarray):
    cam = p.renderer.GetActiveCamera()
    aspect = p.renderer.GetTiledAspectRatio()
    mat = cam.GetCompositeProjectionTransformMatrix(aspect, -1, 1)
    m = np.array(
        [[mat.GetElement(r, c) for c in range(4)] for r in range(4)],
        dtype=np.float64,
    )
    n = len(world_pts)
    h = np.ones((n, 4), dtype=np.float64)
    h[:, :3] = world_pts
    clip = (m @ h.T).T
    w = clip[:, 3]
    valid = w > 0
    ndc = np.zeros((n, 2), dtype=np.float64)
    ndc[valid] = clip[valid, :2] / w[valid, None]
    valid &= (
        (ndc[:, 0] >= -1.1) & (ndc[:, 0] <= 1.1) &
        (ndc[:, 1] >= -1.1) & (ndc[:, 1] <= 1.1)
    )
    W, H = p.renderer.GetSize()
    screen = np.column_stack([
        (ndc[:, 0] + 1.0) * 0.5 * W,
        (ndc[:, 1] + 1.0) * 0.5 * H,
    ])
    return screen, valid

def _set_mesh_input(mapper, mesh, p, attr):
    cached = getattr(p, attr, None)
    if (cached is not None
            and cached.GetNumberOfPoints() == mesh.n_points
            and cached.GetNumberOfCells() == mesh.n_cells):
        cached.GetPoints().SetData(
            numpy_to_vtk(mesh.points, deep=False)
        )
        cached.GetPoints().Modified()
        tc = mesh.active_texture_coordinates
        if tc is not None:
            vtk_tc = numpy_to_vtk(tc, deep=True)
            existing = cached.GetPointData().GetTCoords()
            vtk_tc.SetName(
                existing.GetName()
                if existing is not None
                else 'TextureCoordinates'
            )
            cached.GetPointData().SetTCoords(vtk_tc)
        cached.Modified()
        mapper.SetInputData(cached)
        return cached
    base = vtk.vtkPolyData()
    base.DeepCopy(mesh)

    tc = mesh.active_texture_coordinates
    if tc is not None:
        vtk_tc = numpy_to_vtk(tc, deep=True)

        vtk_tc.SetName('TextureCoordinates')
        base.GetPointData().SetTCoords(vtk_tc)

    mapper.SetInputData(base)
    setattr(p, attr, base)
    return base

def _set_flat_line_lighting(prop) -> None:
    prop.SetLighting(False)
    prop.SetAmbient(1.0)
    prop.SetDiffuse(0.0)
    prop.SetSpecular(0.0)

def _set_actor_transform(actor, p) -> None:
    if hasattr(p, '_norm_center') and hasattr(p, '_norm_scale'):
        cx, cy, cz = p._norm_center
        s = p._norm_scale
        actor.SetOrigin(cx, cy, cz)
        actor.SetScale(s, s, s)
        actor.SetPosition(0.0, 0.0, 0.0)

def _setup_occluder_actor(p, mesh, polygon_offset: bool = False) -> None:
    mapper = p._mesh_mapper
    actor = p._mesh_actor
    cached = _set_mesh_input(mapper, mesh, p, '_cached_mesh_poly')
    cached.GetPointData().SetNormals(None)
    if polygon_offset:
        cached.GetPointData().SetScalars(None)
    cached.GetPointData().Modified()
    mapper.ScalarVisibilityOff()
    if polygon_offset:
        mapper.SetResolveCoincidentTopologyToPolygonOffset()
        mapper.SetRelativeCoincidentTopologyPolygonOffsetParameters(
            *OFFSET_MESH_BACK
        )
    actor.SetTexture(None)
    prop = actor.GetProperty()
    prop.SetOpacity(getattr(p, '_mesh_opacity', 1.0))
    prop.SetColor(*_hex_to_rgb(COLOR_BG))
    prop.SetLighting(False)
    prop.SetInterpolationToFlat()
    prop.EdgeVisibilityOff()
    prop.SetRepresentationToSurface()
    prop.BackfaceCullingOn()
    actor.VisibilityOn()

def make_3point_lights():
    key = vtk.vtkLight()
    key.SetLightTypeToSceneLight()
    key.SetPosition(1.0, 1.0, 1.0)
    key.SetFocalPoint(0.0, 0.0, 0.0)
    key.SetIntensity(1.0)
    key.SetColor(1.0, 1.0, 1.0)

    fill = vtk.vtkLight()
    fill.SetLightTypeToSceneLight()
    fill.SetPosition(-1.0, 0.5, 0.5)
    fill.SetFocalPoint(0.0, 0.0, 0.0)
    fill.SetIntensity(0.5)
    fill.SetColor(1.0, 1.0, 1.0)

    back = vtk.vtkLight()
    back.SetLightTypeToSceneLight()
    back.SetPosition(0.0, -1.0, -0.5)
    back.SetFocalPoint(0.0, 0.0, 0.0)
    back.SetIntensity(0.3)
    back.SetColor(1.0, 1.0, 1.0)

    return [key, fill, back]
