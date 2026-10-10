"""Single in-process, stoppable speech playback for Webbie.

The same trusted code that speaks can call stop() from another thread.
Only command argument vectors; no shell or external network unless the
owner's existing configured edge-tts provider is already enabled.
"""
from __future__ import annotations
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import threading


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
        self.cancelled.set()
        with self._lock:
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

    def speak(self, message):
        text = str(message or '').strip()
        if not text:
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
