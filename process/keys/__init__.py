def bind_key(plotter, key_const, callback) -> None:
    keys = key_const if isinstance(key_const, list) else [key_const]
    for k in keys:
        plotter.add_key_event(k, callback)

def dispatch_key(dispatch_dict, key_const, callback) -> None:
    keys = key_const if isinstance(key_const, list) else [key_const]
    for k in keys:
        dispatch_dict[k] = callback
