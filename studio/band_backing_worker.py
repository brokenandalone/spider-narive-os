"""Asynchronous owner-approved virtual musician -> backing cue bridge.

No recording device is touched by these rendering workers. The Qt UI
receives a valid cue path only after the private WAV is fully published.
"""
from __future__ import annotations

from copy import deepcopy
from PyQt5.QtCore import QThread, pyqtSignal

try:
    from .backing_cue import render_score_backing, render_song_backing
    from .song_arranger_engine import Song
except ImportError:
    from backing_cue import render_score_backing, render_song_backing
    from song_arranger_engine import Song

class BandBackingWorker(QThread):
    finished_cue = pyqtSignal(bool, str, int, str)
    def __init__(self, *, score=None, song=None, default_bank=None,
                 part_banks=None, channels=None, rate=48000, parent=None):
        super().__init__(parent)
        if (score is None) == (song is None):
            raise ValueError("Choose exactly one source for the virtual band backing")
        self.score = deepcopy(score) if score is not None else None
        self.song = Song.from_dict(song.as_dict()) if song is not None else None
        self.default_bank = default_bank
        self.part_banks = dict(part_banks or {})
        self.channels = list(channels or [])
        self.rate = rate

    def run(self):
        try:
            if self.score is not None:
                path, details = render_score_backing(
                    self.score, self.default_bank,
                    part_banks=self.part_banks, channels=self.channels,
                    rate=self.rate)
            else:
                path, details = render_song_backing(self.song, rate=self.rate)
            self.finished_cue.emit(True, str(path), details["rate"], "")
        except (ValueError, OSError, RuntimeError, TypeError) as error:
            self.finished_cue.emit(False, "", 0, str(error)[:360])
