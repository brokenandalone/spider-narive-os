"""Single in-process, stoppable speech playback for Webbie.

The same trusted code that speaks can call stop() from another thread.
Only command argument vectors; no shell or external network unless the
owner's existing configured edge-tts provider is already enabled.
"""
from __future__ import annotations
import os
import re
from pathlib import Path
import shutil
import subprocess
import tempfile
import threading


def clean_spoken_text(text):
    """Strip visual Markdown without changing the user's underlying words.

    This is the recovered owner-installed speech cleanup adapted to the
    existing STOP-aware resident player, not a competing TTS process.
    """
    value = str(text or "")
    value = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", value)
    value = value.replace("\x60\x60\x60", "").replace("\x60", "")
    value = re.sub(r"(?m)^\s{0,3}#{1,6}\s*", "", value)
    value = re.sub(r"(?m)^\s*>\s?", "", value)
    value = re.sub(r"(?m)^\s*[-+•]\s+", "", value)
    for marker in ("***", "**", "__", "*"):
        value = value.replace(marker, "")
    value = re.sub(r"[ \t]+", " ", value)
    value = re.sub(r"\n{3,}", "\n\n", value)
    return value.strip()


class InterruptibleSpeech:
    def __init__(self, *, popen=None, which=None, edge_tts=None,
                 voice='en-AU-NatashaNeural', offline_voice='en-au+f3'):
        self.popen = popen or subprocess.Popen
        self.which = which or shutil.which
        self.edge_tts = edge_tts
        self.voice = voice
        self.offline_voice = offline_voice
        self.cancelled = threading.Event()
        self._lock = threading.RLock()
        self._active = None

    def stop(self):
        # Use the same lock as speak() so a late STOP cannot be cleared by
        # a not-yet-started playback. No requirement to hold it during wait().
        with self._lock:
            self.cancelled.set()
            current = self._active
        if current is not None and current.poll() is None:
            try:
                current.terminate()
            except (OSError, ProcessLookupError):
                pass
        return {'stop_requested': True}

    def _execute(self, argv, timeout=90):
        if self.cancelled.is_set():
            return False
        proc = self.popen(
            argv, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL, start_new_session=True)
        with self._lock:
            self._active = proc
        try:
            if self.cancelled.is_set():
                proc.terminate()
            try:
                result = proc.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                proc.terminate()
                try:
                    proc.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait(timeout=2)
                return False
            return result == 0 and not self.cancelled.is_set()
        finally:
            with self._lock:
                if self._active is proc:
                    self._active = None

    def speak(self, message, *, may_start=None):
        text = clean_spoken_text(message)
        if not text:
            return False
        # Revalidate the originating voice generation while holding the
        # playback lock. STOP invalidates that generation before stop().
        # This eliminates the window where cancelled.clear() could undo STOP.
        with self._lock:
            if may_start is not None and not may_start():
                return False
            self.cancelled.clear()
        path = None
        try:
            edge = self.edge_tts
            if edge is None:
                edge = next((p for p in (
                    '/opt/spider-webbie/bin/edge-tts', '/usr/local/bin/edge-tts',
                    self.which('edge-tts')) if p and Path(p).is_file()), None)
            player = self.which('mpv')
            if edge and player:
                with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as tmp:
                    path = tmp.name
                if self._execute([edge, '--voice', self.voice, '--text', text,
                                  '--write-media', path], timeout=70):
                    if not self.cancelled.is_set():
                        return self._execute([player, '--no-video', '--really-quiet',
                                              path], timeout=120)
            if self.cancelled.is_set():
                return False
            offline = self.which('espeak-ng')
            if offline:
                return self._execute([offline, '-v', self.offline_voice,
                                      '-s', '165', text], timeout=120)
            return False
        finally:
            if path:
                try:
                    os.unlink(path)
                except OSError:
                    pass
