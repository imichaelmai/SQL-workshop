from __future__ import annotations

import math
import unittest
import wave

from fl_melody_generator.analysis import analyze_audio_file


def write_sine(path, frequency: float = 440.0, duration: float = 1.0, sample_rate: int = 8000) -> None:
    frames = bytearray()
    for index in range(int(sample_rate * duration)):
        sample = int(32767 * 0.5 * math.sin(2 * math.pi * frequency * index / sample_rate))
        frames.extend(sample.to_bytes(2, "little", signed=True))
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(sample_rate)
        handle.writeframes(bytes(frames))


class AnalyzeAudioFileTests(unittest.TestCase):
    def test_detects_notes_and_generates_material(self) -> None:
        with self.subTest("sine wave analysis"):
            import tempfile
            from pathlib import Path

            with tempfile.TemporaryDirectory() as directory:
                audio_path = Path(directory) / "lead.wav"
                write_sine(audio_path)

                analysis = analyze_audio_file(audio_path, window_seconds=0.25)

        self.assertEqual(analysis.sample_rate, 8000)
        self.assertEqual(analysis.duration, 1.0)
        self.assertTrue(analysis.detected_notes)
        self.assertTrue(any(note.name.startswith("A") for note in analysis.detected_notes))
        self.assertTrue(analysis.chords)
        self.assertTrue(analysis.melody)


if __name__ == "__main__":
    unittest.main()
