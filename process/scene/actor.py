import time
import logging
import vtk

import configs.defaults as _cfg

from configs.defaults import (
    WIDTH_ISO_LINE, TYPE_TUBE, COLOR_ISO_LINE,
    COLOR_WIREFRAME, WIDTH_WIREFRAME,
    OFFSET_MESH_BACK,
    COLOR_MESH_QUALITY, COLOR_DEPTH,
    EDGE_FEATURE_ANGLE, COLOR_EDGE, WIDTH_EDGE,
    COLOR_BBOX, BBOX_WIDTH,
    VTX_LABEL_COLOR,
    VTX_POINT_COLOR, VTX_POINT_SIZE,
    VTX_PICK_COLOR, VTX_PICK_SIZE,
    FNORMAL_TIP_LENGTH, FNORMAL_TIP_RADIUS,
    FNORMAL_TIP_RESOLUTION, FNORMAL_SHAFT_RADIUS,
    FNORMAL_SHAFT_RESOLUTION, FNORMAL_SCALE, FNORMAL_CMAP,
)
from process.mode.common import _hex_to_rgb, _make_vtk_lut

logger = logging.getLogger(__name__)

def init_render_actor(plotter):
    t0 = time.perf_counter()

    mapper = vtk.vtkPolyDataMapper()
    actor = vtk.vtkActor()
    actor.SetMapper(mapper)
    plotter.renderer.AddActor(actor)
    plotter._mesh_mapper = mapper
    plotter._mesh_actor = actor
    plotter._prev_mode = None

    iso_mapper = vtk.vtkPolyDataMapper()
    iso_actor = vtk.vtkActor()
    iso_actor.SetMapper(iso_mapper)
    iso_prop = iso_actor.GetProperty()
    iso_prop.SetLineWidth(WIDTH_ISO_LINE)
    iso_prop.SetRenderLinesAsTubes(int(TYPE_TUBE))
    if COLOR_ISO_LINE.startswith('#'):
        iso_prop.SetColor(*_hex_to_rgb(COLOR_ISO_LINE))
        plotter._iso_lut = None
    else:
        plotter._iso_lut = _make_vtk_lut(COLOR_ISO_LINE)

    if COLOR_WIREFRAME.startswith('#'):
        plotter._wire_lut = None
    else:
        plotter._wire_lut = _make_vtk_lut(COLOR_WIREFRAME)
    plotter._quality_lut = _make_vtk_lut(COLOR_MESH_QUALITY)
    if COLOR_DEPTH.startswith('#'):
        plotter._depth_lut = None
    else:
        plotter._depth_lut = _make_vtk_lut(COLOR_DEPTH)
    iso_actor.VisibilityOff()
    plotter.renderer.AddActor(iso_actor)
    plotter._iso_mapper = iso_mapper
    plotter._iso_actor = iso_actor

    wire_mapper = vtk.vtkPolyDataMapper()
    wire_actor = vtk.vtkActor()
    wire_actor.SetMapper(wire_mapper)
    wire_prop = wire_actor.GetProperty()
    wire_prop.SetRepresentationToWireframe()
    wire_prop.SetLineWidth(WIDTH_WIREFRAME)
    wire_prop.SetRenderLinesAsTubes(int(TYPE_TUBE))
    wire_actor.VisibilityOff()
    plotter.renderer.AddActor(wire_actor)
    plotter._wire_mapper = wire_mapper
    plotter._wire_actor = wire_actor

    if COLOR_EDGE.startswith('#'):
        plotter._edge_lut = None
    else:
        plotter._edge_lut = _make_vtk_lut(COLOR_EDGE)
    edge_filter = vtk.vtkFeatureEdges()
    edge_filter.SetInputData(vtk.vtkPolyData())
    edge_filter.BoundaryEdgesOn()
    edge_filter.FeatureEdgesOn()
    edge_filter.ManifoldEdgesOff()
    edge_filter.NonManifoldEdgesOn()
    edge_filter.SetFeatureAngle(EDGE_FEATURE_ANGLE)
    edge_filter.ColoringOff()
    edge_mapper = vtk.vtkPolyDataMapper()
    edge_mapper.SetInputConnection(edge_filter.GetOutputPort())
    edge_actor = vtk.vtkActor()
    edge_actor.SetMapper(edge_mapper)
    edge_prop = edge_actor.GetProperty()
    edge_prop.SetLineWidth(WIDTH_EDGE)
    edge_actor.VisibilityOff()
    plotter.renderer.AddActor(edge_actor)
    plotter._edge_filter = edge_filter
    plotter._edge_mapper = edge_mapper
    plotter._edge_actor = edge_actor

    bounds = getattr(
        plotter, '_norm_bounds', (-1, 1, -1, 1, -1, 1)
    )
    outline = vtk.vtkOutlineSource()
    outline.SetBounds(*bounds)
    outline.Update()
    bbox_mapper = vtk.vtkPolyDataMapper()
    bbox_mapper.SetInputConnection(outline.GetOutputPort())
    bbox_actor = vtk.vtkActor()
    bbox_actor.SetMapper(bbox_mapper)
    bbox_prop = bbox_actor.GetProperty()
    bbox_prop.SetColor(*_hex_to_rgb(COLOR_BBOX))
    bbox_prop.SetLineWidth(BBOX_WIDTH)
    if getattr(plotter, '_is_bbox', False):
        bbox_actor.VisibilityOn()
    else:
        bbox_actor.VisibilityOff()
    plotter.renderer.AddActor(bbox_actor)
    plotter._bbox_outline = outline
    plotter._bbox_actor = bbox_actor

    vtx_mapper = vtk.vtkLabeledDataMapper()
    vtx_mapper.SetLabelModeToLabelScalars()
    vtx_mapper.SetLabelFormat('%d')

    ltp = vtx_mapper.GetLabelTextProperty()
    ltp.SetFontFamilyToCourier()
    ltp.SetFontSize(_cfg.VTX_LABEL_FONT_SIZE)
    ltp.SetColor(*_hex_to_rgb(VTX_LABEL_COLOR))
    ltp.BoldOff()
    ltp.ShadowOff()
    ltp.ItalicOff()
    vtx_actor = vtk.vtkActor2D()
    vtx_actor.SetMapper(vtx_mapper)
    vtx_actor.VisibilityOff()
    plotter.renderer.AddActor2D(vtx_actor)
    plotter._vtx_label_mapper = vtx_mapper
    plotter._vtx_label_actor = vtx_actor
    plotter._vtx_text_actors = []

    vtx_glyph = vtk.vtkVertexGlyphFilter()
    vtx_glyph.SetInputData(vtk.vtkPolyData())
    vtx_pt_mapper = vtk.vtkPolyDataMapper()
    vtx_pt_mapper.SetInputConnection(vtx_glyph.GetOutputPort())
    vtx_pt_mapper.ScalarVisibilityOff()

    vtx_pt_mapper.SetResolveCoincidentTopologyToPolygonOffset()
    vtx_pt_mapper.SetRelativeCoincidentTopologyPointOffsetParameter(
        -1.0
    )
    vtx_pt_actor = vtk.vtkActor()
    vtx_pt_actor.SetMapper(vtx_pt_mapper)
    pt_prop = vtx_pt_actor.GetProperty()
    pt_prop.SetColor(*_hex_to_rgb(VTX_POINT_COLOR))
    pt_prop.SetPointSize(VTX_POINT_SIZE)
    pt_prop.SetLighting(False)
    pt_prop.RenderPointsAsSpheresOn()
    vtx_pt_actor.VisibilityOff()
    plotter.renderer.AddActor(vtx_pt_actor)
    plotter._vtx_glyph = vtx_glyph
    plotter._vtx_point_actor = vtx_pt_actor

    arrow_src = vtk.vtkArrowSource()
    arrow_src.SetTipLength(FNORMAL_TIP_LENGTH)
    arrow_src.SetTipRadius(FNORMAL_TIP_RADIUS)
    arrow_src.SetTipResolution(FNORMAL_TIP_RESOLUTION)
    arrow_src.SetShaftRadius(FNORMAL_SHAFT_RADIUS)
    arrow_src.SetShaftResolution(FNORMAL_SHAFT_RESOLUTION)
    arrow_src.Update()

    fnormal_glyph = vtk.vtkGlyph3D()
    fnormal_glyph.SetInputData(vtk.vtkPolyData())
    fnormal_glyph.SetSourceConnection(arrow_src.GetOutputPort())
    fnormal_glyph.SetVectorModeToUseNormal()
    fnormal_glyph.OrientOn()
    fnormal_glyph.SetScaleModeToDataScalingOff()
    fnormal_glyph.SetScaleFactor(FNORMAL_SCALE)

    fnormal_lut = _make_vtk_lut(FNORMAL_CMAP)

    fnormal_mapper = vtk.vtkPolyDataMapper()
    fnormal_mapper.SetInputConnection(fnormal_glyph.GetOutputPort())
    fnormal_mapper.SetLookupTable(fnormal_lut)
    fnormal_mapper.SetScalarRange(-1.0, 1.0)
    fnormal_mapper.ScalarVisibilityOn()

    fnormal_actor = vtk.vtkActor()
    fnormal_actor.SetMapper(fnormal_mapper)
    fnormal_prop = fnormal_actor.GetProperty()
    fnormal_prop.SetLighting(False)
    fnormal_prop.SetAmbient(1.0)
    fnormal_prop.SetDiffuse(0.0)
    fnormal_prop.SetSpecular(0.0)
    fnormal_actor.VisibilityOff()
    plotter.renderer.AddActor(fnormal_actor)
    plotter._fnormal_glyph = fnormal_glyph
    plotter._fnormal_mapper = fnormal_mapper
    plotter._fnormal_actor = fnormal_actor

    pick_pts = vtk.vtkPoints()
    pick_pts.InsertNextPoint(0.0, 0.0, 0.0)
    pick_poly = vtk.vtkPolyData()
    pick_poly.SetPoints(pick_pts)
    pick_glyph = vtk.vtkVertexGlyphFilter()
    pick_glyph.SetInputData(pick_poly)
    pick_mapper = vtk.vtkPolyDataMapper()
    pick_mapper.SetInputConnection(pick_glyph.GetOutputPort())
    pick_mapper.ScalarVisibilityOff()
    pick_mapper.SetResolveCoincidentTopologyToPolygonOffset()
    pick_mapper.SetRelativeCoincidentTopologyPointOffsetParameter(
        -1.0
    )
    pick_actor = vtk.vtkActor()
    pick_actor.SetMapper(pick_mapper)
    pick_prop = pick_actor.GetProperty()
    pick_prop.SetColor(*_hex_to_rgb(VTX_PICK_COLOR))
    pick_prop.SetPointSize(VTX_PICK_SIZE)
    pick_prop.SetLighting(False)
    pick_prop.RenderPointsAsSpheresOn()
    pick_actor.VisibilityOff()
    plotter.renderer.AddActor(pick_actor)
    plotter._vtx_pick_pts = pick_pts
    plotter._vtx_pick_poly = pick_poly
    plotter._vtx_sel_actor = pick_actor

    pick_txt = vtk.vtkTextActor()
    pick_txt.SetInput('')
    pick_tp = pick_txt.GetTextProperty()
    pick_tp.SetFontFamilyToCourier()
    pick_tp.SetFontSize(_cfg.VTX_LABEL_FONT_SIZE + 2)
    pick_tp.SetColor(*_hex_to_rgb(VTX_PICK_COLOR))
    pick_tp.BoldOn()
    pick_tp.ShadowOff()
    pick_txt.GetPositionCoordinate().SetCoordinateSystemToDisplay()
    pick_txt.SetPosition(10, 36)
    pick_txt.VisibilityOff()
    plotter.renderer.AddActor2D(pick_txt)
    plotter._vtx_pick_text = pick_txt

    logger.debug(
        'init_render_actor done: %.4fs', time.perf_counter() - t0
    )

def init_actors(plotter) -> None:
    t0 = time.perf_counter()
    init_render_actor(plotter)
    cx, cy, cz = plotter._norm_center
    s = plotter._norm_scale
    for actor in (
        plotter._mesh_actor, plotter._wire_actor, plotter._edge_actor
    ):
        actor.SetOrigin(cx, cy, cz)
        actor.SetScale(s, s, s)
        actor.SetPosition(0.0, 0.0, 0.0)
    logger.debug('init_actors: %.4fs', time.perf_counter() - t0)
