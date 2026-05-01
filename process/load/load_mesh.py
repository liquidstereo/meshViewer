import os
import logging

import pyvista as pv

from process.load.load_np import load_npy_as_polydata, load_npz_as_polydata
from process.load.load_pointcloud import is_gs_ply

logger = logging.getLogger(__name__)

_NPY_EXT = '.npy'
_NPZ_INPUT_EXT = '.npz'
_GLTF_EXTS = {'.glb', '.gltf'}
_UV_CANDIDATE_NAMES = (
    'TEXCOORD_0', 'TEXCOORD_1',
    'TextureCoordinates', 'Texture Coordinates', 'UV',
)

def _fix_gltf_v_flip(mesh: pv.PolyData) -> None:
    tc = mesh.active_texture_coordinates
    if tc is None:
        return
    fixed = tc.copy()
    fixed[:, 1] = 1.0 - fixed[:, 1]
    mesh.active_texture_coordinates = fixed
    logger.info('glTF UV V coordinate restored (1 - V).')

def _activate_texture_coords(mesh: pv.PolyData) -> None:
    if mesh.active_texture_coordinates is not None:
        logger.debug('UV already active: skipping activation.')
        return
    pd = mesh.GetPointData()
    n_arrays = pd.GetNumberOfArrays()
    for i in range(n_arrays):
        name = pd.GetArrayName(i)
        if not name:
            continue
        lower_name = name.lower()
        if any(p in lower_name for p in ('uv', 'tex', 'coord')):
            arr = pd.GetArray(name)
            if arr and arr.GetNumberOfComponents() >= 2:
                pd.SetActiveTCoords(name)
                mesh.Modified()
                logger.info(
                    'Texture coordinates activated by pattern:'
                    ' "%s" (components=%d)',
                    name, arr.GetNumberOfComponents(),
                )
                return
    logger.debug('No valid UV array found by pattern matching.')

def _collect_polydata_blocks(mb: pv.MultiBlock) -> list:
    blocks = []
    for i in range(mb.n_blocks):
        blk = mb[i]
        if blk is None:
            continue
        if isinstance(blk, pv.PolyData) and blk.n_points > 0:
            blocks.append(blk)
        elif isinstance(blk, pv.MultiBlock):
            blocks.extend(_collect_polydata_blocks(blk))
    return blocks

def _merge_gltf_blocks(blocks: list) -> pv.PolyData:
    import vtk as _vtk
    uv_blocks = [
        b for b in blocks
        if any(
            b.GetPointData().GetArray(n) is not None
            for n in _UV_CANDIDATE_NAMES
        )
    ]
    target = uv_blocks if uv_blocks else blocks
    if len(target) == 1:
        return target[0]
    append = _vtk.vtkAppendPolyData()
    for b in target:
        append.AddInputData(b)
    append.Update()
    return pv.wrap(append.GetOutput())

def read_polydata(path: str) -> pv.PolyData:
    ext = os.path.splitext(path)[1].lower()
    if ext == _NPY_EXT:
        return load_npy_as_polydata(path)
    if ext == _NPZ_INPUT_EXT:
        return load_npz_as_polydata(path)
    result = pv.read(path)
    is_gltf = ext in _GLTF_EXTS
    if not isinstance(result, pv.MultiBlock):
        if not isinstance(result, pv.PolyData):
            result = result.extract_surface()
        _activate_texture_coords(result)
        if is_gltf:
            _fix_gltf_v_flip(result)
        return result
    blocks = _collect_polydata_blocks(result)
    if blocks:
        poly = _merge_gltf_blocks(blocks)
    else:
        combined = result.combine()
        poly = (
            combined if isinstance(combined, pv.PolyData)
            else combined.extract_surface(algorithm='dataset_surface')
        )
    _activate_texture_coords(poly)
    if is_gltf:
        _fix_gltf_v_flip(poly)
    return poly
