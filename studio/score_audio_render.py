"""Performance MIDI export and optional licensed SoundFont rendering.

A standards-based MIDI arrangement is always available. High-quality rendered
audio requires installed FluidSynth plus a soundfont file supplied/licensed by
the user. Nothing is downloaded or installed; subprocess uses argv, no shell.
"""
from __future__ import annotations
import os
from pathlib import Path
import shutil
import struct
import subprocess
import tempfile
from .score_performance import Performance, PPQ
from .midi_song_export import vlq, chunk, track_bytes

CHANNELS = [i for i in range(16) if i != 9]

def performance_midi(performance):
    score = performance.validate()
    if not score.notes:
        raise ValueError("Score contains no playable notes")
    tempo = round(60_000_000 / score.bpm)
    meta = track_bytes([(0, 0, b"\xff\x51\x03" + tempo.to_bytes(3,"big")),
                        (0, 1, b"\xff\x58\x04\x04\x02\x18\x08")], "Spider Score", 
                        max(n.start+n.duration for n in score.notes))
    tracks = [meta]
    for index, name in enumerate(score.tracks):
        if index >= len(CHANNELS):
            raise ValueError("MIDI format 1 exporter supports at most 15 channels")
        channel = CHANNELS[index]
        # GM: piano, clean electric guitar, fingered bass, others piano.
        low = name.lower()
        program = 24 if "guitar" in low else 33 if "bass" in low else 0
        events = [(0, 0, bytes([0xC0 | channel, program]))]
        end = 0
        for note in score.notes:
            if note.track != index:
                continue
            end = max(end, note.start+note.duration)
            events.append((note.start, 2, bytes([0x90|channel,note.pitch,note.velocity])))
            events.append((note.start+note.duration, 1, bytes([0x80|channel,note.pitch,0])))
        tracks.append(track_bytes(events, name, end))
    return chunk(b"MThd",struct.pack(">HHH",1,len(tracks),PPQ)) + b"".join(tracks)

def export_performance_midi(score, destination):
    target = Path(destination)
    if not target.parent.is_dir():
        raise FileNotFoundError("Output folder does not exist")
    data = performance_midi(score)
    tmp = None
    try:
        fd,tmp = tempfile.mkstemp(prefix=".spider-score-",suffix=".mid.tmp",dir=str(target.parent))
        with os.fdopen(fd,"wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp,target)
    finally:
        if tmp is not None:
            Path(tmp).unlink(missing_ok=True)

def soundfont_ready(soundfont):
    """Do not imply professional sampling unless an actual bank is configured."""
    binary = shutil.which("fluidsynth")
    bank = Path(soundfont).expanduser() if soundfont else None
    return bool(binary and bank and bank.is_file() and bank.suffix.lower() in (".sf2",".sf3"))

def render_soundfont(score, soundfont, destination, samplerate=44100):
    """Render offline via FluidSynth CLI, leaving imported scores/samples alone.

    This is a bounded synchronous function: callers should use a Qt worker.
    """
    if not soundfont_ready(soundfont):
        raise RuntimeError("FluidSynth executable and licensed .sf2/.sf3 SoundFont required")
    if type(samplerate) is not int or samplerate not in (44100,48000):
        raise ValueError("Supported output rates are 44.1 and 48 kHz")
    target = Path(destination)
    if not target.parent.is_dir():
        raise FileNotFoundError("Audio output folder missing")
    bank = Path(soundfont).expanduser().resolve()
    if target.resolve() == bank:
        raise ValueError("Cannot overwrite selected SoundFont")
    with tempfile.TemporaryDirectory(prefix=".spider-score-") as scratch:
        midi = Path(scratch)/"performance.mid"
        wav = Path(scratch)/"render.wav"
        export_performance_midi(score,midi)
        cmd = [shutil.which("fluidsynth"), "-ni", "-F", str(wav),
               "-r", str(samplerate), str(bank),str(midi)]
        # No shell; bounded runtime and temporary output rather than partial final.
        process = subprocess.run(cmd,capture_output=True,text=True,timeout=180,check=False)
        if process.returncode != 0 or not wav.is_file() or wav.stat().st_size < 44:
            raise RuntimeError("SoundFont rendering failed: " + (process.stderr or "")[-260:])
        fd,temp = tempfile.mkstemp(prefix=".spider-score-",suffix=".wav.tmp",dir=str(target.parent))
        os.close(fd)
        try:
            shutil.copyfile(wav,temp)
            os.replace(temp,target)
        finally:
            Path(temp).unlink(missing_ok=True)
