import logging
import math
import os

import numpy as np
import pyvista as pv
import vtk
from vtk.util import numpy_support

from configs.settings import HDRI_PATH, HDRI_INTENSITY, HDRI_ENABLE

logger = logging.getLogger(__name__)

def setup_hdri(plotter) -> None:
    plotter._hdri_tex = None
    plotter._hdri_ibl_cached = False
    if not HDRI_ENABLE:
        logger.debug('setup_hdri: skipped (HDRI_ENABLE=False)')
        return
    if not os.path.isfile(HDRI_PATH):
        logger.warning('HDRI file not found: %s', HDRI_PATH)
        return

    try:
        reader = vtk.vtkHDRReader()
        reader.SetFileName(HDRI_PATH)
        reader.Update()
        img_data = reader.GetOutput()

        scalars = img_data.GetPointData().GetScalars()
        arr = numpy_support.vtk_to_numpy(scalars).astype(np.float32)
        arr *= HDRI_INTENSITY
        new_scalars = numpy_support.numpy_to_vtk(
            arr, deep=True, array_type=vtk.VTK_FLOAT
        )
        new_scalars.SetName(scalars.GetName())
        img_data.GetPointData().SetScalars(new_scalars)

        vtk_tex = vtk.vtkTexture()
        vtk_tex.SetInputDataObject(img_data)
        vtk_tex.MipmapOn()
        vtk_tex.InterpolateOn()

        hdr = pv.Texture(vtk_tex)
        hdr.mipmap = True
        hdr.interpolate = True
        plotter._hdri_tex = hdr
        logger.debug(
            'setup_hdri: loaded %s (intensity=%.2f)', HDRI_PATH, HDRI_INTENSITY
        )
    except Exception as e:
        logger.warning(
            'setup_hdri: failed to load HDRI (%s): %s', HDRI_PATH, e
        )

def enable_hdri(plotter) -> None:
    tex = getattr(plotter, '_hdri_tex', None)
    if tex is None:
        return

    renderer = plotter.renderer
    renderer.RemoveAllLights()
    renderer.AutomaticLightCreationOff()

    if getattr(plotter, '_hdri_ibl_cached', False):
        renderer.UseImageBasedLightingOn()
        renderer.SetBackgroundTexture(tex)
        renderer.Modified()
    else:
        plotter.set_environment_texture(tex)
        plotter._hdri_ibl_cached = True
    logger.debug('enable_hdri: IBL ON (scene lights cleared)')

def disable_hdri(plotter) -> None:
    if getattr(plotter, '_hdri_tex', None) is None:
        return

    plotter.renderer.UseImageBasedLightingOff()
    plotter.renderer.SetBackgroundTexture(None)
    plotter.renderer.Modified()
    logger.debug('disable_hdri: IBL OFF')

def rotate_hdri(plotter, angle_deg: float) -> None:
    rad = math.radians(angle_deg)
    plotter.renderer.SetEnvironmentRight(math.cos(rad), 0.0, -math.sin(rad))
    logger.debug('rotate_hdri: angle=%.1f deg', angle_deg)
