from process.mode.vtx import apply_vtx_pick

_PICK_DRAG_THRESHOLD = 5

def register(p, trigger):
    _pick_press_pos = [0, 0]

    def _on_vtx_press(caller, _):
        if not getattr(p, '_is_vtx', False):
            return
        pos = caller.GetEventPosition()
        _pick_press_pos[0] = pos[0]
        _pick_press_pos[1] = pos[1]

    def _on_vtx_release(caller, _):
        if not getattr(p, '_is_vtx', False):
            return
        rx, ry = caller.GetEventPosition()
        if (abs(rx - _pick_press_pos[0]) < _PICK_DRAG_THRESHOLD
                and abs(ry - _pick_press_pos[1]) < _PICK_DRAG_THRESHOLD):
            apply_vtx_pick(p, rx, ry)
            trigger()

    interactor = p.iren.interactor
    interactor.AddObserver('LeftButtonPressEvent', _on_vtx_press)
    interactor.AddObserver('LeftButtonReleaseEvent', _on_vtx_release)
