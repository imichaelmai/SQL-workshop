"""Small Standard MIDI File writer used by the melody generator."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class MidiNote:
    """A MIDI note event in seconds."""

    pitch: int
    start: float
    duration: float
    velocity: int = 90
    channel: int = 0


def write_midi_file(path: str | Path, notes: list[MidiNote], tempo_bpm: int = 120, ticks_per_quarter: int = 480) -> None:
    """Write notes to a format-0 .mid file compatible with FL Studio."""

    output_path = Path(path)
    events: list[tuple[int, bytes]] = []
    microseconds_per_quarter = int(60_000_000 / tempo_bpm)
    events.append((0, b"\xff\x51\x03" + microseconds_per_quarter.to_bytes(3, "big")))

    for note in notes:
        start_tick = _seconds_to_ticks(note.start, tempo_bpm, ticks_per_quarter)
        end_tick = _seconds_to_ticks(note.start + note.duration, tempo_bpm, ticks_per_quarter)
        channel = max(0, min(15, note.channel))
        pitch = max(0, min(127, note.pitch))
        velocity = max(1, min(127, note.velocity))
        events.append((start_tick, bytes([0x90 | channel, pitch, velocity])))
        events.append((max(start_tick + 1, end_tick), bytes([0x80 | channel, pitch, 0])))

    events.sort(key=lambda event: (event[0], event[1][0] == 0x80))
    track = bytearray()
    previous_tick = 0
    for tick, payload in events:
        delta = max(0, tick - previous_tick)
        track.extend(_variable_length_quantity(delta))
        track.extend(payload)
        previous_tick = tick
    track.extend(b"\x00\xff\x2f\x00")

    header = b"MThd" + (6).to_bytes(4, "big") + (0).to_bytes(2, "big") + (1).to_bytes(2, "big") + ticks_per_quarter.to_bytes(2, "big")
    chunk = b"MTrk" + len(track).to_bytes(4, "big") + bytes(track)
    output_path.write_bytes(header + chunk)


def _seconds_to_ticks(seconds: float, tempo_bpm: int, ticks_per_quarter: int) -> int:
    beats = seconds * tempo_bpm / 60.0
    return int(round(beats * ticks_per_quarter))


def _variable_length_quantity(value: int) -> bytes:
    if value < 0:
        raise ValueError("MIDI variable length quantity cannot be negative")
    buffer = value & 0x7F
    value >>= 7
    while value:
        buffer <<= 8
        buffer |= ((value & 0x7F) | 0x80)
        value >>= 7
    output = bytearray()
    while True:
        output.append(buffer & 0xFF)
        if buffer & 0x80:
            buffer >>= 8
        else:
            break
    return bytes(output)
