from configs.settings import COLOR_GRID, GRID_FONT_FAMILY, GRID_WIDTH

def _apply_grid_line_width(ax, width: float) -> None:
    for _prop in (
        ax.GetXAxesGridlinesProperty(), ax.GetYAxesGridlinesProperty(),
        ax.GetZAxesGridlinesProperty(), ax.GetXAxesLinesProperty(),
        ax.GetYAxesLinesProperty(), ax.GetZAxesLinesProperty(),
    ):
        _prop.SetLineWidth(width)
    ax.Modified()

def setup_grid(plotter):
    kwargs = dict(
        color=COLOR_GRID,
        font_family=GRID_FONT_FAMILY,
        xtitle='X', ytitle='Y', ztitle='Z',
    )
    if hasattr(plotter, '_norm_bounds'):
        kwargs['bounds'] = plotter._norm_bounds
    plotter.show_grid(**kwargs)
    plotter._grid_actor = getattr(
        plotter.renderer, 'cube_axes_actor', None
    )
    if plotter._grid_actor is not None:
        _apply_grid_line_width(plotter._grid_actor, GRID_WIDTH)

def update_grid_bounds(plotter, bounds: tuple) -> None:
    if hasattr(plotter, '_bbox_outline'):
        plotter._bbox_outline.SetBounds(*bounds)
        plotter._bbox_outline.Update()
    grid_actor = getattr(plotter, '_grid_actor', None)
    if grid_actor is not None:
        grid_actor.SetBounds(*bounds)
