# FL Melody Generator

A lightweight Windows desktop companion for FL Studio producers. Import an audio file, let the tool identify the strongest notes and estimated key, then generate harmonizing chords and a complementary melody that can be exported as a MIDI file for FL Studio.

This prototype is designed to help producers who have an instrumental idea but no vocalist or topline yet. It creates MIDI material that can be dragged into FL Studio and assigned to any synth, piano, vocal chop, or instrument plugin.

## Features

- **Audio import with basic codecs:** supports uncompressed WAV, AIFF, and AIFC files through the Python standard library.
- **Song analysis:** converts stereo to mono, scans short windows for dominant pitch, labels detected notes, and estimates the key and mode.
- **Harmony generation:** creates a chord progression in the detected key to complement the input audio.
- **Melody generation:** creates a MIDI-ready countermelody that follows the detected key.
- **Playback controls:** can play and stop WAV source audio on Windows and opens the generated MIDI preview with the system MIDI handler.
- **FL Studio workflow:** exports a Standard MIDI File (`.mid`) that can be imported or dragged into FL Studio.

## Requirements

- Python 3.11 or newer.
- Windows is recommended for native WAV playback. The analyzer and MIDI exporter also run on macOS/Linux.
- No third-party Python packages are required for the application.

## Run the desktop app

```bash
python -m fl_melody_generator
```

## Workflow

1. Click **Open Audio** and choose a WAV, AIFF, or AIFC file.
2. Click **Analyze + Generate** to detect notes, estimate key, and create harmony/melody material.
3. Use **Play Song** to preview the WAV input on Windows.
4. Use **Play Generated MIDI** to open the generated MIDI preview in the system MIDI player.
5. Click **Save MIDI** and drag the saved `.mid` file into FL Studio.

## Notes and limitations

- MP3 decoding is intentionally not included because Python's standard library does not ship an MP3 decoder. Convert MP3s to WAV before importing.
- The pitch detector is monophonic-friendly and works best with clean leads, vocals, basses, or stems. Dense full mixes may produce less accurate note detection.
- Generated chords and melodies are a starting point for producer editing, not a replacement for arrangement decisions.

## Run tests

```bash
python -m unittest discover -s tests
```
