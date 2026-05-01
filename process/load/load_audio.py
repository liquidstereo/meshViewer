import os

from alive_progress import alive_bar

def load_audio_data(
    audio_path: str,
    start: float,
    end: float | None,
    fps: int,
) -> tuple:
    from process.audio.pipeline import (
        prepare_audio_data, PREPARE_AUDIO_STEPS,
    )
    with alive_bar(
        PREPARE_AUDIO_STEPS, spinner=None,
        title='PROCESSING AUDIO DATA...',
        title_length=25, length=15,
        dual_line=True, stats=True,
        elapsed=True, manual=False,
        enrich_print=False, force_tty=True,
    ) as bar:
        result = prepare_audio_data(audio_path, start, end, fps, bar=bar)
        bar.title = 'AUDIO PROCESSING COMPLETE'
    return result
