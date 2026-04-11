import logging
import vtk

from process.mode.common import make_3point_lights

logger = logging.getLogger(__name__)

def apply_lighting(plotter):
    renderer = plotter.renderer
    renderer.RemoveAllLights()
    renderer.AutomaticLightCreationOff()
    if plotter._is_lighting:
        for light in make_3point_lights():
            plotter.add_light(light)
    else:
        headlight = vtk.vtkLight()
        headlight.SetLightTypeToHeadlight()
        headlight.SetIntensity(1.0)
        renderer.AddLight(headlight)
    logger.debug(
        'apply_lighting: 3point=%s', plotter._is_lighting
    )
