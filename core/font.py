import logging
import subprocess
from functools import lru_cache

logger = logging.getLogger(__name__)

_FC_MATCH_CMD = 'fc-match'
_FC_FORMAT = '%{family}|%{file}'
_FC_TIMEOUT_SEC = 3.0

_GENERIC_FAMILIES = ('monospace', 'sans-serif', 'serif')

_BUILTIN_FAMILIES = ('courier', 'arial', 'times')

def _query_fontconfig(name: str) -> tuple:
    try:
        result = subprocess.run(
            [_FC_MATCH_CMD, '-f', _FC_FORMAT, name],
            capture_output=True, text=True, timeout=_FC_TIMEOUT_SEC,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        logger.debug('fc-match unavailable for %r: %s', name, exc)
        return '', ''
    if result.returncode != 0:
        return '', ''
    families, _, path = result.stdout.strip().partition('|')
    return families, path

def _is_exact_match(requested: str, families: str) -> bool:
    target = requested.lower()
    return any(f.strip().lower() == target for f in families.split(','))

@lru_cache(maxsize=32)
def _resolve_single(name: str) -> str:
    families, path = _query_fontconfig(name)
    if not path:
        return ''
    if name.lower() in _GENERIC_FAMILIES:
        return path

    if _is_exact_match(name, families):
        return path
    return ''

def is_builtin_family(name: str) -> bool:
    return name.lower() in _BUILTIN_FAMILIES

@lru_cache(maxsize=32)
def resolve_font_file(name: str, priority: tuple) -> str:
    if name in priority:
        chain = priority[priority.index(name):]
    else:
        chain = (name,) + priority
    for candidate in chain:
        path = _resolve_single(candidate)
        if path:
            return path
    logger.warning('No font file resolved for %r (chain=%s)', name, chain)
    return ''
