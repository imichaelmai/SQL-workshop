"""FL Melody Generator: lightweight audio analysis and MIDI harmony creation."""

from .analysis import AudioAnalysis, analyze_audio_file
from .midi import MidiNote, write_midi_file

__all__ = ["AudioAnalysis", "MidiNote", "analyze_audio_file", "write_midi_file"]
