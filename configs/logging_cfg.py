import os
import logging

from configs.defaults import LOG_DIR, LOG_FORMAT, LOG_MSEC_FORMAT

def setup_logging(
    input_name: str,
    level: int = logging.INFO,
) -> None:
    os.makedirs(LOG_DIR, exist_ok=True)
    log_path = os.path.join(LOG_DIR, f'{input_name}.log')

    handler = logging.FileHandler(log_path, mode='w', encoding='utf-8')
    handler.setLevel(level)
    formatter = logging.Formatter(LOG_FORMAT)
    formatter.default_msec_format = LOG_MSEC_FORMAT
    handler.setFormatter(formatter)

    logging.basicConfig(level=logging.DEBUG, handlers=[handler], force=True)
    logging.getLogger('matplotlib').setLevel(logging.WARNING)
