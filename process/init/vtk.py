import logging
import vtk

from configs.colorize import Msg

logger = logging.getLogger(__name__)

class _VtkLogOutputWindow(vtk.vtkOutputWindow):

    def DisplayText(self, text):
        text = text.strip()
        if text:
            logger.debug('VTK: %s', text)

    def DisplayWarningText(self, text):
        text = text.strip()
        if text:
            logger.warning('VTK: %s', text)

    def DisplayErrorText(self, text):
        text = text.strip()
        if text:
            logger.error('VTK: %s', text)

    def DisplayGenericWarningText(self, text):
        text = text.strip()
        if text:
            logger.warning('VTK: %s', text)

    def DisplayDebugText(self, text):
        text = text.strip()
        if text:
            logger.debug('VTK: %s', text)

def init_vtk() -> None:

    print('\u2014')
    Msg.Dim(f'Processing\u2026 Please Wait\u2026', flush=True)

    global _vtk_output_window_instance
    _vtk_output_window_instance = _VtkLogOutputWindow()
    vtk.vtkOutputWindow.SetInstance(_vtk_output_window_instance)
    vtk.vtkMathTextUtilities.SetInstance(None)
    try:
        tr = vtk.vtkTextRenderer.GetInstance()
        tr.SetDefaultBackend(1)
    except Exception as e:
        logger.warning('vtkTextRenderer FreeType not set: %s', e)

    vtk.vtkMapper.SetResolveCoincidentTopologyPolygonOffsetParameters(
        0.0, 0.0
    )
