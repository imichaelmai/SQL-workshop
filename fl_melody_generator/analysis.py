"""Audio analysis helpers for melody and harmony generation.

The analyzer intentionally uses only Python's standard library so the tool can
run on a fresh Windows machine without compiling audio DSP dependencies. It
supports uncompressed WAV and AIFF/AIFC files and extracts a practical musical
summary: dominant notes, an estimated key, tempo proxy, and generated harmony.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import aifc
import audioop
import math
import wave

NOTE_NAMES = ("C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B")
MAJOR_PROFILE = (6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88)
MINOR_PROFILE = (6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17)
MAJOR_SCALE = (0, 2, 4, 5, 7, 9, 11)
MINOR_SCALE = (0, 2, 3, 5, 7, 8, 10)


@dataclass(frozen=True)
class DetectedNote:
    """A note detected in a short window of the source audio."""

    name: str
    midi: int
    frequency: float
    start: float
    duration: float
    confidence: float


@dataclass(frozen=True)
class GeneratedChord:
    """A generated chord intended to harmonize with the input audio."""

    name: str
    midi_notes: tuple[int, ...]
    start: float
    duration: float


@dataclass(frozen=True)
class GeneratedMelodyNote:
    """A generated single-note countermelody event."""

    midi: int
    start: float
    duration: float
    velocity: int


@dataclass(frozen=True)
class AudioAnalysis:
    """The complete musical summary for one analyzed audio file."""

    source_path: str
    sample_rate: int
    duration: float
    key: str
    mode: str
    detected_notes: tuple[DetectedNote, ...]
    chords: tuple[GeneratedChord, ...]
    melody: tuple[GeneratedMelodyNote, ...]


def analyze_audio_file(path: str | Path, window_seconds: float = 0.50) -> AudioAnalysis:
    """Analyze an audio file and generate complementary MIDI-ready material.

    Args:
        path: Path to a WAV, AIFF, or AIFC file.
        window_seconds: Analysis window size. Shorter windows are more reactive;
            longer windows are smoother.

    Returns:
        AudioAnalysis with detected notes, estimated key/mode, generated chords,
        and generated countermelody notes.
    """

    audio_path = Path(path)
    sample_rate, samples = _read_mono_samples(audio_path)
    duration = len(samples) / sample_rate if sample_rate else 0.0
    window_size = max(512, int(sample_rate * window_seconds))
    detected = tuple(_detect_notes(samples, sample_rate, window_size))
    key_root, mode = _estimate_key(detected)
    chords = tuple(_generate_chords(key_root, mode, duration))
    melody = tuple(_generate_melody(key_root, mode, chords))
    return AudioAnalysis(
        source_path=str(audio_path),
        sample_rate=sample_rate,
        duration=duration,
        key=NOTE_NAMES[key_root],
        mode=mode,
        detected_notes=detected,
        chords=chords,
        melody=melody,
    )


def _read_mono_samples(path: Path) -> tuple[int, list[float]]:
    suffix = path.suffix.lower()
    if suffix in {".wav", ".wave"}:
        with wave.open(str(path), "rb") as handle:
            return _decode_pcm(handle)
    if suffix in {".aif", ".aiff", ".aifc"}:
        with aifc.open(str(path), "rb") as handle:
            return _decode_pcm(handle)
    raise ValueError(f"Unsupported codec '{path.suffix}'. Use WAV, AIFF, or AIFC.")


def _decode_pcm(handle: wave.Wave_read | aifc.Aifc_read) -> tuple[int, list[float]]:
    channels = handle.getnchannels()
    sample_width = handle.getsampwidth()
    frame_rate = handle.getframerate()
    frames = handle.readframes(handle.getnframes())
    if channels > 1:
        frames = audioop.tomono(frames, sample_width, 0.5, 0.5)
    if sample_width != 2:
        frames = audioop.lin2lin(frames, sample_width, 2)
        sample_width = 2
    integers = [int.from_bytes(frames[i : i + sample_width], "little", signed=True) for i in range(0, len(frames), sample_width)]
    max_amplitude = float(2 ** (8 * sample_width - 1))
    return frame_rate, [sample / max_amplitude for sample in integers]


def _detect_notes(samples: list[float], sample_rate: int, window_size: int) -> list[DetectedNote]:
    notes: list[DetectedNote] = []
    hop = window_size
    for offset in range(0, len(samples), hop):
        window = samples[offset : offset + window_size]
        if len(window) < window_size // 2:
            continue
        rms = math.sqrt(sum(sample * sample for sample in window) / len(window))
        if rms < 0.015:
            continue
        frequency, confidence = _estimate_frequency(window, sample_rate)
        if not frequency:
            continue
        midi = _frequency_to_midi(frequency)
        notes.append(
            DetectedNote(
                name=_midi_to_name(midi),
                midi=midi,
                frequency=frequency,
                start=offset / sample_rate,
                duration=len(window) / sample_rate,
                confidence=confidence,
            )
        )
    return notes


def _estimate_frequency(window: list[float], sample_rate: int) -> tuple[float | None, float]:
    min_freq = 65.0
    max_freq = 1200.0
    min_lag = max(1, int(sample_rate / max_freq))
    max_lag = min(len(window) - 2, int(sample_rate / min_freq))
    if max_lag <= min_lag:
        return None, 0.0

    best_lag = min_lag
    best_score = -1.0
    energy = sum(sample * sample for sample in window) or 1.0
    for lag in range(min_lag, max_lag):
        score = sum(window[i] * window[i + lag] for i in range(len(window) - lag)) / energy
        if score > best_score:
            best_score = score
            best_lag = lag
    if best_score < 0.25:
        return None, best_score
    return sample_rate / best_lag, min(1.0, best_score)


def _frequency_to_midi(frequency: float) -> int:
    return int(round(69 + 12 * math.log2(frequency / 440.0)))


def _midi_to_name(midi: int) -> str:
    octave = midi // 12 - 1
    return f"{NOTE_NAMES[midi % 12]}{octave}"


def _estimate_key(notes: tuple[DetectedNote, ...]) -> tuple[int, str]:
    if not notes:
        return 0, "major"
    histogram = [0.0] * 12
    for note in notes:
        histogram[note.midi % 12] += note.confidence * note.duration

    best_root = 0
    best_mode = "major"
    best_score = -1.0
    for root in range(12):
        major_score = sum(histogram[(root + i) % 12] * MAJOR_PROFILE[i] for i in range(12))
        minor_score = sum(histogram[(root + i) % 12] * MINOR_PROFILE[i] for i in range(12))
        if major_score > best_score:
            best_root, best_mode, best_score = root, "major", major_score
        if minor_score > best_score:
            best_root, best_mode, best_score = root, "minor", minor_score
    return best_root, best_mode


def _generate_chords(root: int, mode: str, duration: float) -> list[GeneratedChord]:
    scale = MINOR_SCALE if mode == "minor" else MAJOR_SCALE
    qualities = ("min", "dim", "maj", "min") if mode == "minor" else ("maj", "maj", "min", "maj")
    degrees = (0, 5, 3, 4) if mode == "minor" else (0, 3, 4, 5)
    chord_length = 2.0
    total = max(chord_length, duration or 8.0)
    chords: list[GeneratedChord] = []
    step = 0
    start = 0.0
    while start < total:
        degree = degrees[step % len(degrees)]
        chord_root_pc = (root + scale[degree]) % 12
        quality = qualities[step % len(qualities)]
        intervals = (0, 3, 6) if quality == "dim" else ((0, 3, 7) if quality == "min" else (0, 4, 7))
        base = 48 + chord_root_pc
        while base > 60:
            base -= 12
        chords.append(
            GeneratedChord(
                name=f"{NOTE_NAMES[chord_root_pc]} {quality}",
                midi_notes=tuple(base + interval for interval in intervals),
                start=start,
                duration=min(chord_length, total - start),
            )
        )
        start += chord_length
        step += 1
    return chords


def _generate_melody(root: int, mode: str, chords: tuple[GeneratedChord, ...]) -> list[GeneratedMelodyNote]:
    scale = MINOR_SCALE if mode == "minor" else MAJOR_SCALE
    melody: list[GeneratedMelodyNote] = []
    pattern = (0, 2, 4, 5, 4, 2, 1, 2)
    for chord_index, chord in enumerate(chords):
        beat = chord.duration / 4
        for index in range(4):
            degree = pattern[(chord_index * 4 + index) % len(pattern)]
            octave = 72 if index % 2 == 0 else 74
            midi = octave + ((root + scale[degree % len(scale)]) % 12)
            melody.append(GeneratedMelodyNote(midi=midi, start=chord.start + beat * index, duration=beat * 0.85, velocity=88))
    return melody
