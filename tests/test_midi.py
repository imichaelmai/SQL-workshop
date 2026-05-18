from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from fl_melody_generator.midi import MidiNote, write_midi_file


class WriteMidiFileTests(unittest.TestCase):
    def test_creates_standard_midi_header(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            midi_path = Path(directory) / "generated.mid"

            write_midi_file(midi_path, [MidiNote(pitch=60, start=0.0, duration=1.0)])

            data = midi_path.read_bytes()
        self.assertTrue(data.startswith(b"MThd"))
        self.assertIn(b"MTrk", data)
        self.assertTrue(data.endswith(b"\x00\xff\x2f\x00"))


if __name__ == "__main__":
    unittest.main()
