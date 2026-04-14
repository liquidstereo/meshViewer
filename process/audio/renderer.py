import logging

import numpy as np
import pyvista as pv
import vtk
from vtk.util.numpy_support import numpy_to_vtk

from configs.settings import (
    COLOR_BG,
    RENDER_LINE_SMOOTHING,
    TYPE_TUBE,
    OFFSET_MESH_BACK,
    STARTUP_AUDIO_MODE,
    AUDIO_ISO_AXIS,
    AUDIO_COLOR_AXIS,
    AUDIO_ISO_COUNT_DEFAULT,
    AUDIO_ISOLINE_CMAP,
    AUDIO_WIREFRAME_CMAP,
    AUDIO_MESH_CMAP,
    AUDIO_DEPTH_CMAP,
    AUDIO_EDGE_CMAP,
    AUDIO_QUALITY_CMAP,
    AUDIO_FNORMAL_CMAP,
    AUDIO_GRID_Y_MAX,
    AUDIO_FREQ_NORM_MAX,
    AUDIO_ISOLINE_WIDTH,
    AUDIO_WIREFRAME_LINE_WIDTH,
    AUDIO_EDGE_FEATURE_ANGLE,
    AUDIO_FNORMAL_SPATIAL_INTERVAL,
    AUDIO_FNORMAL_SCALE,
    DEFAULT_BBOX,
    DEFAULT_BACKFACE,
    AUDIO_COLOR_BBOX,
    BBOX_WIDTH,
)
from process.mode.common import _make_vtk_lut, _get_cam_dir
from process.audio.geometry import process_geometry, update_isoline_and_color

logger = logging.getLogger(__name__)

class WaterfallRenderer:

    def __init__(
        self,
        plotter: pv.Plotter,
        x_grid: np.ndarray,
        z_grid: np.ndarray,
        global_max: float,
        mode: str = STARTUP_AUDIO_MODE,
        iso_axis: str = AUDIO_ISO_AXIS,
        color_axis: str = AUDIO_COLOR_AXIS,
        iso_count: int = AUDIO_ISO_COUNT_DEFAULT,
    ):
        _VALID = (
            'ISOLINE', 'MESH', 'WIREFRAME',
            'DEPTH', 'EDGE', 'FACE_NORMAL', 'QUALITY',
        )
        if mode not in _VALID:
            raise ValueError(f'Unsupported mode: {mode}')
        self.plotter = plotter
        self.x_grid = x_grid
        self.z_grid = z_grid
        self._global_max = global_max
        self.mode = mode
        self._iso_axis = iso_axis
        self._color_axis = color_axis
        self._iso_count = iso_count
        self._is_turntable = True
        self.keep_running = True
        self._depth_axis = 3
        self._fnormal_axis = 3
        self._edge_feature_angle = AUDIO_EDGE_FEATURE_ANGLE
        self._edge_filter = None
        self._fnormal_vtk_poly = None
        self._fnormal_glyph = None
        self._lut = _make_vtk_lut(self._cmap_for_mode(mode))

        dummy = np.zeros_like(x_grid, dtype=np.float32)
        dummy[0, 0] = 0.1
        self.base_poly = process_geometry(
            dummy, x_grid, z_grid, global_max
        )
        self.iso_poly = pv.PolyData()
        self.main_actor = None
        self.body_actor = None
        self.bbox_actor = None

    def init_actors(self) -> None:
        self._init_actors()
        if DEFAULT_BBOX:
            self._setup_bbox()

    def switch_mode(self, new_mode: str) -> None:
        if new_mode == self.mode:
            return
        _VALID = (
            'ISOLINE', 'MESH', 'WIREFRAME',
            'DEPTH', 'EDGE', 'FACE_NORMAL', 'QUALITY',
        )
        if new_mode not in _VALID:
            raise ValueError(f'Unsupported mode: {new_mode}')
        for act in (self.main_actor, self.body_actor):
            if act is not None:
                self.plotter.remove_actor(act)
        self.main_actor = None
        self.body_actor = None
        self.iso_poly = pv.PolyData()
        self.mode = new_mode
        self._init_actors()
        if self.bbox_actor is not None:
            self._setup_bbox()

    def _cmap_for_mode(self, mode: str) -> str:
        return {
            'ISOLINE':      AUDIO_ISOLINE_CMAP,
            'WIREFRAME':    AUDIO_WIREFRAME_CMAP,
            'MESH':         AUDIO_MESH_CMAP,
            'DEPTH':        AUDIO_DEPTH_CMAP,
            'EDGE':         AUDIO_EDGE_CMAP,
            'FACE_NORMAL':  AUDIO_FNORMAL_CMAP,
            'QUALITY':      AUDIO_QUALITY_CMAP,
        }[mode]

    def _init_actors(self) -> None:
        dispatch = {
            'ISOLINE':      self._init_isoline_actors,
            'MESH':         self._init_mesh_actors,
            'WIREFRAME':    self._init_wireframe_actors,
            'DEPTH':        self._init_depth_actors,
            'EDGE':         self._init_edge_actors,
            'FACE_NORMAL':  self._init_fnormal_actors,
            'QUALITY':      self._init_quality_actors,
        }
        dispatch[self.mode]()

    def _setup_bbox(self) -> None:
        init_bounds = [
            0.0, AUDIO_FREQ_NORM_MAX,
            0.0, AUDIO_GRID_Y_MAX,
            0.0, AUDIO_GRID_Y_MAX,
        ]
        self.bbox_actor = self.plotter.add_mesh(
            pv.Box(bounds=init_bounds),
            color=AUDIO_COLOR_BBOX,
            style='wireframe',
            name='bbox',
        )
        prop = self.bbox_actor.GetProperty()
        prop.SetLineWidth(BBOX_WIDTH)
        prop.SetLighting(False)

        self.bbox_actor.mapper.SetResolveCoincidentTopologyToShiftZBuffer()

        self.plotter._bbox_actor = self.bbox_actor

    def _update_bbox(self) -> None:
        axes = getattr(
            self.plotter.renderer, 'cube_axes_actor', None
        )
        if axes is None:
            return
        b = axes.GetBounds()
        new_box = pv.Box(bounds=list(b))
        self.bbox_actor.mapper.SetInputData(new_box)
        self.bbox_actor.mapper.Update()

    def _init_isoline_actors(self) -> None:
        cmap = self._cmap_for_mode('ISOLINE')
        self._lut = _make_vtk_lut(cmap)
        self.body_actor = self.plotter.add_mesh(
            self.base_poly,
            color=COLOR_BG,
            style='surface',
            lighting=False,
            name='wf_body',
        )
        body_mapper = self.body_actor.mapper
        body_mapper.SetResolveCoincidentTopologyToPolygonOffset()
        body_mapper.SetRelativeCoincidentTopologyPolygonOffsetParameters(
            *OFFSET_MESH_BACK
        )
        self.body_actor.prop.SetInterpolationToFlat()

        self.body_actor.prop.BackfaceCullingOn()
        if not DEFAULT_BACKFACE:
            self.body_actor.VisibilityOff()

        scalar_range = update_isoline_and_color(
            self.plotter, self.base_poly, self.iso_poly,
            self._iso_axis, self._color_axis, self._iso_count,
        )
        self.main_actor = self.plotter.add_mesh(
            self.iso_poly,
            cmap=cmap,
            clim=[0, AUDIO_GRID_Y_MAX],
            show_scalar_bar=False,
            line_width=AUDIO_ISOLINE_WIDTH,
            render_lines_as_tubes=TYPE_TUBE,
            name='wf_main',
        )
        main_mapper = self.main_actor.mapper
        main_mapper.SetLookupTable(self._lut)
        main_mapper.ScalarVisibilityOn()
        if scalar_range is not None:
            main_mapper.SetScalarRange(*scalar_range)
        else:
            main_mapper.SetScalarRange(0.0, AUDIO_GRID_Y_MAX)

        if self._iso_axis == 'CAM' or self._color_axis == 'CAM':
            self.plotter.iren.add_observer(
                'ModifiedEvent', self._on_camera_change
            )

    def _init_mesh_actors(self) -> None:
        cmap = self._cmap_for_mode('MESH')
        self._lut = _make_vtk_lut(cmap)
        self.base_poly.point_data['intensity'] = (
            self.base_poly.points[:, 1].astype(np.float32)
        )
        self.base_poly.set_active_scalars('intensity')
        self.main_actor = self.plotter.add_mesh(
            self.base_poly,
            cmap=cmap,
            clim=[0, AUDIO_GRID_Y_MAX],
            show_scalar_bar=False,
            name='wf_main',
        )
        self.main_actor.mapper.SetLookupTable(self._lut)
        prop = self.main_actor.GetProperty()
        if DEFAULT_BACKFACE:
            prop.BackfaceCullingOff()
        else:
            prop.BackfaceCullingOn()

    def _init_wireframe_actors(self) -> None:
        cmap = self._cmap_for_mode('WIREFRAME')
        self._lut = _make_vtk_lut(cmap)

        self.body_actor = self.plotter.add_mesh(
            self.base_poly,
            color=COLOR_BG,
            style='surface',
            lighting=False,
            name='wf_body',
        )
        self.body_actor.prop.SetInterpolationToFlat()

        self.body_actor.prop.BackfaceCullingOn()
        bm = self.body_actor.GetMapper()
        bm.SetResolveCoincidentTopologyToPolygonOffset()
        bm.SetRelativeCoincidentTopologyPolygonOffsetParameters(
            *OFFSET_MESH_BACK
        )
        if not DEFAULT_BACKFACE:
            self.body_actor.VisibilityOff()

        self.base_poly.point_data['intensity'] = (
            self.base_poly.points[:, 1].astype(np.float32)
        )
        self.base_poly.set_active_scalars('intensity')
        self.main_actor = self.plotter.add_mesh(
            self.base_poly,
            cmap=cmap,
            clim=[0, AUDIO_GRID_Y_MAX],
            show_scalar_bar=False,
            name='wf_main',
        )
        self.main_actor.mapper.SetLookupTable(self._lut)
        self.main_actor.prop.SetRepresentationToWireframe()
        self.main_actor.prop.SetLineWidth(AUDIO_WIREFRAME_LINE_WIDTH)
        self.main_actor.prop.SetRenderLinesAsTubes(int(TYPE_TUBE))

    def _compute_depth(
        self, points: np.ndarray, axis: int | None = None
    ) -> np.ndarray:
        ax = self._depth_axis if axis is None else axis
        if ax != 3:
            return points[:, ax].astype(np.float32)
        cam = self.plotter.renderer.GetActiveCamera()
        cam_dir = np.array(cam.GetDirectionOfProjection())
        cam_dir /= np.linalg.norm(cam_dir) + 1e-12
        cam_pos = np.array(cam.GetPosition())
        return np.dot(points - cam_pos, cam_dir).astype(np.float32)

    def _set_edge_scalars(self) -> tuple[float, float]:
        depth = self._compute_depth(self.base_poly.points, axis=3)
        vtk_d = numpy_to_vtk(depth, deep=True)
        vtk_d.SetName('intensity')
        self.base_poly.GetPointData().SetScalars(vtk_d)
        self.base_poly.GetPointData().Modified()
        self.base_poly.Modified()
        lo = float(depth.min())
        hi = float(depth.max()) if depth.max() > lo else lo + 1.0
        return lo, hi

    def _init_depth_actors(self) -> None:
        cmap = self._cmap_for_mode('DEPTH')
        self._lut = _make_vtk_lut(cmap)
        depth = self._compute_depth(self.base_poly.points)
        self.base_poly.point_data['depth'] = depth
        self.base_poly.set_active_scalars('depth')
        lo = float(depth.min())
        hi = float(depth.max()) if depth.max() > lo else lo + 1.0
        self.main_actor = self.plotter.add_mesh(
            self.base_poly,
            cmap=cmap,
            clim=[lo, hi],
            show_scalar_bar=False,
            lighting=False,
            name='wf_main',
        )
        self.main_actor.mapper.SetLookupTable(self._lut)
        self.main_actor.mapper.ScalarVisibilityOn()
        self.main_actor.mapper.SetScalarRange(lo, hi)
        prop = self.main_actor.GetProperty()
        if DEFAULT_BACKFACE:
            prop.BackfaceCullingOff()
        else:
            prop.BackfaceCullingOn()

    def _init_edge_actors(self) -> None:
        cmap = self._cmap_for_mode('EDGE')
        self._lut = _make_vtk_lut(cmap)

        self.body_actor = self.plotter.add_mesh(
            self.base_poly, color=COLOR_BG, style='surface',
            lighting=False, name='wf_body',
        )
        self.body_actor.prop.SetInterpolationToFlat()
        self.body_actor.prop.BackfaceCullingOn()
        bm = self.body_actor.mapper
        bm.SetResolveCoincidentTopologyToPolygonOffset()
        bm.SetRelativeCoincidentTopologyPolygonOffsetParameters(
            *OFFSET_MESH_BACK
        )
        if not DEFAULT_BACKFACE:
            self.body_actor.VisibilityOff()

        self._edge_filter = vtk.vtkFeatureEdges()
        self._edge_filter.SetInputData(self.base_poly)
        self._edge_filter.SetFeatureAngle(self._edge_feature_angle)
        self._edge_filter.BoundaryEdgesOn()
        self._edge_filter.FeatureEdgesOn()
        self._edge_filter.NonManifoldEdgesOff()
        self._edge_filter.ManifoldEdgesOff()
        self._edge_filter.ColoringOff()

        lo, hi = self._set_edge_scalars()
        self._edge_filter.Update()
        self.main_actor = self.plotter.add_mesh(
            pv.wrap(self._edge_filter.GetOutput()),
            cmap=cmap, clim=[lo, hi],
            show_scalar_bar=False,
            line_width=AUDIO_ISOLINE_WIDTH,
            render_lines_as_tubes=TYPE_TUBE,
            name='wf_main',
        )
        mm = self.main_actor.mapper
        mm.SetInputConnection(self._edge_filter.GetOutputPort())
        mm.SetScalarModeToUsePointData()
        mm.SetLookupTable(self._lut)
        mm.SetScalarRange(lo, hi)
        mm.ScalarVisibilityOn()

    def _update_fnormal(self) -> None:
        centers = self.base_poly.cell_centers().points
        if len(centers) == 0:
            return
        tmp = self.base_poly.copy()
        tmp.compute_normals(
            cell_normals=True, point_normals=False, inplace=True,
        )
        normals = tmp.cell_data['Normals']

        grid_cells = np.floor(
            centers / AUDIO_FNORMAL_SPATIAL_INTERVAL
        ).astype(np.int64)
        _, idx = np.unique(grid_cells, axis=0, return_index=True)
        idx = np.sort(idx)
        sel_c = centers[idx]
        sel_n = normals[idx]
        vtk_pts = vtk.vtkPoints()
        vtk_pts.SetData(numpy_to_vtk(sel_c, deep=True))
        vtk_n = numpy_to_vtk(sel_n, deep=True)
        vtk_n.SetName('Normals')
        if self._fnormal_axis == 3:
            cam_dir = _get_cam_dir(self.plotter)
            scalar_data = -(sel_n @ cam_dir).astype(np.float32)
        else:
            scalar_data = sel_n[:, self._fnormal_axis].astype(np.float32)
        vtk_sc = numpy_to_vtk(scalar_data, deep=True)
        vtk_sc.SetName('FlowScalar')
        self._fnormal_vtk_poly.SetPoints(vtk_pts)
        self._fnormal_vtk_poly.GetPointData().SetNormals(vtk_n)
        self._fnormal_vtk_poly.GetPointData().SetScalars(vtk_sc)
        self._fnormal_vtk_poly.Modified()
        self._fnormal_glyph.Update()

    def _init_fnormal_actors(self) -> None:
        cmap = self._cmap_for_mode('FACE_NORMAL')
        self._lut = _make_vtk_lut(cmap)

        self.body_actor = self.plotter.add_mesh(
            self.base_poly, color=COLOR_BG, style='surface',
            lighting=False, name='wf_body',
        )
        self.body_actor.prop.SetInterpolationToFlat()
        self.body_actor.prop.BackfaceCullingOn()
        bm = self.body_actor.mapper
        bm.SetResolveCoincidentTopologyToPolygonOffset()
        bm.SetRelativeCoincidentTopologyPolygonOffsetParameters(
            *OFFSET_MESH_BACK
        )
        if not DEFAULT_BACKFACE:
            self.body_actor.VisibilityOff()

        arrow = vtk.vtkArrowSource()
        arrow.SetTipLength(0.35)
        arrow.SetShaftRadius(0.03)
        arrow.Update()
        self._fnormal_vtk_poly = vtk.vtkPolyData()
        self._fnormal_glyph = vtk.vtkGlyph3D()
        self._fnormal_glyph.SetSourceConnection(arrow.GetOutputPort())
        self._fnormal_glyph.SetInputData(self._fnormal_vtk_poly)
        self._fnormal_glyph.SetVectorModeToUseNormal()
        self._fnormal_glyph.OrientOn()
        self._fnormal_glyph.SetScaleModeToDataScalingOff()
        self._fnormal_glyph.SetScaleFactor(AUDIO_FNORMAL_SCALE)
        self._update_fnormal()
        self.main_actor = self.plotter.add_mesh(
            pv.wrap(self._fnormal_glyph.GetOutput()),
            cmap=cmap, clim=[0, AUDIO_GRID_Y_MAX],
            show_scalar_bar=False, name='wf_main',
        )
        mm = self.main_actor.mapper
        mm.SetInputConnection(self._fnormal_glyph.GetOutputPort())
        mm.SetLookupTable(self._lut)
        mm.SetScalarRange(0.0, AUDIO_GRID_Y_MAX)
        mm.ScalarVisibilityOn()

    def _init_quality_actors(self) -> None:
        cmap = self._cmap_for_mode('QUALITY')
        self._lut = _make_vtk_lut(cmap)
        quality = self.base_poly.cell_quality(
            quality_measure='scaled_jacobian'
        ).cell_data['scaled_jacobian']
        self.base_poly.cell_data['quality'] = quality
        self.base_poly.set_active_scalars('quality', preference='cell')
        lo = float(quality.min())
        hi = float(quality.max()) if quality.max() > lo else lo + 1.0
        self.main_actor = self.plotter.add_mesh(
            self.base_poly,
            cmap=cmap, clim=[lo, hi],
            show_scalar_bar=False,
            name='wf_main',
        )
        mm = self.main_actor.mapper
        mm.SetLookupTable(self._lut)
        mm.SetScalarModeToUseCellData()
        mm.SetScalarRange(lo, hi)
        mm.ScalarVisibilityOn()
        prop = self.main_actor.GetProperty()
        if DEFAULT_BACKFACE:
            prop.BackfaceCullingOff()
        else:
            prop.BackfaceCullingOn()

    def _on_camera_change(self, _obj, _event) -> None:
        if self.mode != 'ISOLINE':
            return
        if self._iso_axis != 'CAM' and self._color_axis != 'CAM':
            return
        scalar_range = update_isoline_and_color(
            self.plotter, self.base_poly, self.iso_poly,
            self._iso_axis, self._color_axis, self._iso_count,
        )
        if scalar_range is not None:
            self.main_actor.mapper.SetScalarRange(*scalar_range)
            self.plotter._cmap_range = scalar_range

    def update(self, buffer: np.ndarray) -> None:
        new_poly = process_geometry(
            buffer, self.x_grid, self.z_grid, self._global_max
        )
        self.base_poly.points = new_poly.points

        if self.mode == 'ISOLINE':
            scalar_range = update_isoline_and_color(
                self.plotter, self.base_poly, self.iso_poly,
                self._iso_axis, self._color_axis, self._iso_count,
            )
            if scalar_range is not None:
                self.main_actor.mapper.SetScalarRange(*scalar_range)
                self.plotter._cmap_range = scalar_range
            self.main_actor.mapper.Update()
            self.body_actor.mapper.Update()
        elif self.mode in ('MESH', 'WIREFRAME'):
            self.base_poly.point_data['intensity'] = (
                self.base_poly.points[:, 1].astype(np.float32)
            )
            self.main_actor.mapper.Update()
            if self.body_actor:
                self.body_actor.mapper.Update()
        elif self.mode == 'DEPTH':
            depth = self._compute_depth(self.base_poly.points)
            self.base_poly.point_data['depth'] = depth
            lo = float(depth.min())
            hi = float(depth.max()) if depth.max() > lo else lo + 1.0
            self.main_actor.mapper.SetScalarRange(lo, hi)
            self.main_actor.mapper.Update()
            self.plotter._cmap_range = (lo, hi)
            _AXIS_NAMES = ('X', 'Y', 'Z', 'CAM')
            self.plotter._cmap_title = (
                f'DEPTH.{_AXIS_NAMES[self._depth_axis]}'
            )
        elif self.mode == 'EDGE':
            self._edge_filter.Update()
            self.main_actor.mapper.Update()
            if self.body_actor:
                self.body_actor.mapper.Update()
        elif self.mode == 'FACE_NORMAL':
            self._update_fnormal()
            if self.body_actor:
                self.body_actor.mapper.Update()
        elif self.mode == 'QUALITY':
            quality = self.base_poly.cell_quality(
                quality_measure='scaled_jacobian'
            ).cell_data['scaled_jacobian']
            self.base_poly.cell_data['quality'] = quality
            lo = float(quality.min())
            hi = float(quality.max()) if quality.max() > lo else lo + 1.0
            self.main_actor.mapper.SetScalarRange(lo, hi)
            self.main_actor.mapper.Update()
            self.plotter._cmap_range = (lo, hi)
            self.plotter._cmap_title = 'QUALITY'

        if DEFAULT_BBOX and self.bbox_actor is not None:
            self._update_bbox()

    def toggle_smooth_shading(self) -> bool:
        smooth = not getattr(self.plotter, '_is_smooth_shading', False)
        self.plotter._is_smooth_shading = smooth
        for actor in (self.main_actor, self.body_actor):
            if actor is None:
                continue
            prop = actor.GetProperty()
            if smooth:
                prop.SetInterpolationToPhong()
            else:
                prop.SetInterpolationToFlat()
        return smooth
