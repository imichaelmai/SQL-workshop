"""Tkinter Windows desktop UI for FL Melody Generator."""

from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from .analysis import AudioAnalysis, analyze_audio_file
from .midi import MidiNote, write_midi_file

try:
    import winsound
except ImportError:  # Non-Windows test/dev environments can still import the app.
    winsound = None


class MelodyGeneratorApp(tk.Tk):
    """Desktop app that analyzes audio and exports FL Studio-compatible MIDI."""

    def __init__(self) -> None:
        super().__init__()
        self.title("FL Melody Generator")
        self.geometry("760x520")
        self.audio_path: Path | None = None
        self.analysis: AudioAnalysis | None = None
        self.preview_midi = Path(tempfile.gettempdir()) / "fl_melody_generator_preview.mid"
        self._build_ui()

    def _build_ui(self) -> None:
        frame = ttk.Frame(self, padding=16)
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frame, text="FL Melody Generator", font=("Segoe UI", 20, "bold")).pack(anchor=tk.W)
        ttk.Label(
            frame,
            text="Import a WAV/AIFF song, detect notes and key, then create harmonizing chords and melodies for FL Studio.",
        ).pack(anchor=tk.W, pady=(4, 16))

        button_row = ttk.Frame(frame)
        button_row.pack(fill=tk.X)
        ttk.Button(button_row, text="Open Audio", command=self.open_audio).pack(side=tk.LEFT)
        ttk.Button(button_row, text="Analyze + Generate", command=self.analyze).pack(side=tk.LEFT, padx=8)
        ttk.Button(button_row, text="Play Song", command=self.play_song).pack(side=tk.LEFT)
        ttk.Button(button_row, text="Play Generated MIDI", command=self.play_generated).pack(side=tk.LEFT, padx=8)
        ttk.Button(button_row, text="Pause/Stop", command=self.stop_playback).pack(side=tk.LEFT)
        ttk.Button(button_row, text="Save MIDI", command=self.save_midi).pack(side=tk.RIGHT)

        self.status = tk.StringVar(value="Choose an audio file to begin.")
        ttk.Label(frame, textvariable=self.status).pack(anchor=tk.W, pady=12)

        columns = ("time", "detected", "confidence")
        self.note_table = ttk.Treeview(frame, columns=columns, show="headings", height=8)
        self.note_table.heading("time", text="Start")
        self.note_table.heading("detected", text="Detected Note")
        self.note_table.heading("confidence", text="Confidence")
        self.note_table.pack(fill=tk.BOTH, expand=True)

        self.chord_text = tk.Text(frame, height=8, wrap=tk.WORD)
        self.chord_text.pack(fill=tk.BOTH, expand=True, pady=(12, 0))
        self.chord_text.insert(tk.END, "Generated chords and melody notes will appear here.")
        self.chord_text.configure(state=tk.DISABLED)

    def open_audio(self) -> None:
        file_name = filedialog.askopenfilename(
            title="Open audio file",
            filetypes=(("Basic audio codecs", "*.wav *.wave *.aif *.aiff *.aifc"), ("All files", "*.*")),
        )
        if file_name:
            self.audio_path = Path(file_name)
            self.status.set(f"Loaded {self.audio_path.name}. Ready to analyze.")

    def analyze(self) -> None:
        if not self.audio_path:
            messagebox.showwarning("No audio", "Open a WAV or AIFF file first.")
            return
        try:
            self.analysis = analyze_audio_file(self.audio_path)
        except Exception as exc:  # UI boundary: show user-facing codec/parse errors.
            messagebox.showerror("Analysis failed", str(exc))
            return
        self._render_analysis(self.analysis)
        self._write_preview()

    def play_song(self) -> None:
        if not self.audio_path:
            messagebox.showwarning("No audio", "Open a WAV file first.")
            return
        if winsound and self.audio_path.suffix.lower() in {".wav", ".wave"}:
            winsound.PlaySound(str(self.audio_path), winsound.SND_FILENAME | winsound.SND_ASYNC)
        else:
            messagebox.showinfo("Playback", "Native preview playback is available for WAV files on Windows.")

    def play_generated(self) -> None:
        if not self.analysis:
            messagebox.showwarning("No MIDI", "Analyze a song before previewing generated MIDI.")
            return
        self._write_preview()
        if sys.platform.startswith("win"):
            import os

            os.startfile(self.preview_midi)  # type: ignore[attr-defined]
        else:
            messagebox.showinfo("Preview MIDI", f"Generated MIDI preview saved to {self.preview_midi}.")

    def stop_playback(self) -> None:
        if winsound:
            winsound.PlaySound(None, winsound.SND_PURGE)
        self.status.set("Playback stopped. If MIDI opened in another app, pause it there.")

    def save_midi(self) -> None:
        if not self.analysis:
            messagebox.showwarning("No MIDI", "Analyze a song before saving MIDI.")
            return
        file_name = filedialog.asksaveasfilename(title="Save MIDI", defaultextension=".mid", filetypes=(("MIDI", "*.mid"),))
        if file_name:
            write_midi_file(file_name, self._analysis_to_midi_notes(self.analysis))
            self.status.set(f"Saved MIDI to {file_name}.")

    def _render_analysis(self, analysis: AudioAnalysis) -> None:
        for row in self.note_table.get_children():
            self.note_table.delete(row)
        for note in analysis.detected_notes[:32]:
            self.note_table.insert("", tk.END, values=(f"{note.start:0.2f}s", note.name, f"{note.confidence:0.2f}"))

        self.chord_text.configure(state=tk.NORMAL)
        self.chord_text.delete("1.0", tk.END)
        self.chord_text.insert(tk.END, f"Estimated key: {analysis.key} {analysis.mode}\n")
        self.chord_text.insert(tk.END, f"Duration: {analysis.duration:0.2f}s | Sample rate: {analysis.sample_rate} Hz\n\n")
        self.chord_text.insert(tk.END, "Generated chord progression:\n")
        for chord in analysis.chords:
            self.chord_text.insert(tk.END, f"  {chord.start:0.2f}s - {chord.name} {chord.midi_notes}\n")
        self.chord_text.insert(tk.END, f"\nGenerated melody notes: {len(analysis.melody)} events ready for MIDI export.\n")
        self.chord_text.configure(state=tk.DISABLED)
        self.status.set(f"Analyzed {Path(analysis.source_path).name}: {analysis.key} {analysis.mode}.")

    def _write_preview(self) -> None:
        if self.analysis:
            write_midi_file(self.preview_midi, self._analysis_to_midi_notes(self.analysis))

    @staticmethod
    def _analysis_to_midi_notes(analysis: AudioAnalysis) -> list[MidiNote]:
        midi_notes: list[MidiNote] = []
        for chord in analysis.chords:
            midi_notes.extend(MidiNote(pitch=pitch, start=chord.start, duration=chord.duration, velocity=72) for pitch in chord.midi_notes)
        midi_notes.extend(MidiNote(pitch=note.midi, start=note.start, duration=note.duration, velocity=note.velocity) for note in analysis.melody)
        return midi_notes


def main() -> None:
    app = MelodyGeneratorApp()
    app.mainloop()


if __name__ == "__main__":
    main()
