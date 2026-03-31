import logging

import librosa
import numpy as np

from configs.defaults import (
    AUDIO_TARGET_FPS,
    AUDIO_FREQ_SAMPLES,
    AUDIO_FOCUS_FREQ_RANGE,
    AUDIO_REFERENCE_FRAMES,
    AUDIO_QUIET_THRESHOLD,
)

logger = logging.getLogger(__name__)

PREPARE_AUDIO_STEPS = 6

def _load_raw_signal(
    path: str, start: float, end: float | None, fps: int
) -> tuple:
    raw_sig, sr = librosa.load(
        path, sr=None, offset=start,
        duration=(
            end - start
            if (end is not None and end > start)
            else None
        ),
    )
    hop_len = int(sr / fps)
    total_frames = int(len(raw_sig) / hop_len)
    trimmed_sig = raw_sig[:total_frames * hop_len]
    return trimmed_sig, sr, hop_len, total_frames

def _compute_stft_db(
    sig: np.ndarray, hop_len: int, total_frames: int
) -> np.ndarray:
    stft = np.abs(librosa.stft(sig, n_fft=512, hop_length=hop_len))
    mag = librosa.amplitude_to_db(stft, ref=np.max)
    mag -= mag.min()
    return mag[:, :total_frames]

def _extract_freq_focus(mag: np.ndarray) -> np.ndarray:
    f_s, f_e = AUDIO_FOCUS_FREQ_RANGE
    return mag[f_s:f_e, :].T

def _resample_freq_bins(mag: np.ndarray) -> np.ndarray:
    indices = np.linspace(
        0, mag.shape[1] - 1, AUDIO_FREQ_SAMPLES
    ).astype(int)
    return mag[:, indices]

def _compute_reference_floor(
    mag: np.ndarray, ref_frames: int
) -> np.ndarray:
    n = min(ref_frames, len(mag))
    floor = mag[:n, :].max(axis=0)
    n_silent = int((floor == 0.0).sum())
    logger.debug(
        'Reference floor computed from %d frames: '
        '%d / %d bins are silent',
        n, n_silent, mag.shape[1],
    )
    return floor

def _apply_reference_cutoff(
    mag: np.ndarray, floor: np.ndarray
) -> np.ndarray:
    result = mag.copy()
    result[result <= floor[np.newaxis, :]] = 0.0
    return result

def _flatten_quiet_regions(
    mag: np.ndarray, threshold: float
) -> np.ndarray:
    result = mag.copy()
    frame_max = result.max(axis=1)
    result[frame_max < threshold] = 0.0
    result[result < threshold] = 0.0
    n_zeroed = int((frame_max < threshold).sum())
    logger.debug(
        'Quiet frames zeroed: %d / %d (threshold=%.1f dB)',
        n_zeroed, len(frame_max), threshold,
    )
    return result

def _compute_global_max(mag: np.ndarray) -> float:
    return float(mag.max())

def prepare_audio_data(
    path: str,
    start: float,
    end: float | None,
    fps: int = AUDIO_TARGET_FPS,
    bar: 'callable | None' = None,
) -> tuple:
    sig, sr, hop_len, total_frames = _load_raw_signal(
        path, start, end, fps
    )
    if bar: bar()
    mag = _compute_stft_db(sig, hop_len, total_frames)
    if bar: bar()
    mag = _resample_freq_bins(_extract_freq_focus(mag))
    if bar: bar()
    floor = _compute_reference_floor(mag, AUDIO_REFERENCE_FRAMES)
    mag = _apply_reference_cutoff(mag, floor)
    if bar: bar()
    mag = _flatten_quiet_regions(mag, AUDIO_QUIET_THRESHOLD)
    if bar: bar()
    global_max = _compute_global_max(mag)
    if bar: bar()

    logger.info('Audio loaded: %.2fs, SR: %d', len(sig) / sr, sr)
    logger.info(
        'Target FPS: %d, Total frames: %d, Hop: %d, global_max: %.2f',
        fps, total_frames, hop_len, global_max,
    )
    return mag, total_frames, hop_len, sr, global_max
