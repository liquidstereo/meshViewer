import pyvista as pv
import configs.defaults as _cfg

from configs.defaults import AXIS_COLORS, AXIS_VIEWPORT

def setup_axes_marker(plotter):
    axes = pv.create_axes_marker()
    props = [
        axes.GetXAxisCaptionActor2D().GetCaptionTextProperty(),
        axes.GetYAxisCaptionActor2D().GetCaptionTextProperty(),
        axes.GetZAxisCaptionActor2D().GetCaptionTextProperty()
    ]
    for prop, color in zip(props, AXIS_COLORS):
        prop.SetColor(color)
        prop.SetFontSize(_cfg.AXIS_FONT_SIZE)
        prop.BoldOn()
        prop.ShadowOn()
    plotter.add_orientation_widget(
        axes, viewport=AXIS_VIEWPORT
    )
