import threading

from configs.colorize import Msg

_stop_event: threading.Event | None = None
_thread: threading.Thread | None = None

_LOADING_MSG = Msg.Dim(f'LOADING DATA... PLEASE WAIT...', verbose=True)
_LOADING_INTERVAL = 0.25
_LOADING_COLOR = 'white'

def show_loading() -> None:
    global _stop_event, _thread
    Msg.Plain('—')
    _stop_event = threading.Event()
    _thread = threading.Thread(
        target=Msg.Blink,
        kwargs=dict(
            message=_LOADING_MSG,
            duration=3600.0,
            interval=_LOADING_INTERVAL,
            color=_LOADING_COLOR,
            clear_on_finish=True,
            stop_event=_stop_event,
            upper=False,
        ),
        daemon=True,
    )
    _thread.start()

def hide_loading() -> None:
    global _stop_event, _thread
    if _stop_event is not None:
        _stop_event.set()
        _thread.join(timeout=2.0)
        _stop_event = None
        _thread = None
