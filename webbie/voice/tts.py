#!/usr/bin/env python3
"""Interruptible Webbie TTS with local fallback and bounded spoken replies."""
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import tempfile
import threading
import time

ONLINE_VOICE = "en-AU-NatashaNeural"
OFFLINE_VOICE = "en-au+f3"

def speakable(text, max_chars=650):
    text=str(text or "")
    text=re.sub(r"```[\s\S]*?```"," I have included code in the written response. ",text)
    text=re.sub(r"https?://\S+","a link",text)
    text=re.sub(r"(?m)^\s{0,3}#{1,6}\s+","",text)
    text=re.sub(r"(?m)^\s*[-*]\s+","",text)
    text=re.sub(r"[*_`]+","",text)
    text=re.sub(r"\s+"," ",text).strip()
    if len(text)>max_chars:
        head=text[:max_chars]
        split=max(head.rfind("."),head.rfind("?"),head.rfind("!"))
        text=head[:split+1] if split>max_chars//2 else head.rstrip()+"..."
    return text

class SpeechController:
    """One TTS utterance at a time, with explicit stop and process cleanup."""
    def __init__(self, marker=None, voice=ONLINE_VOICE, offline=OFFLINE_VOICE):
        runtime=Path(os.environ.get("XDG_RUNTIME_DIR",f"/run/user/{os.getuid()}"))/"spider-os"
        self.marker=Path(marker) if marker else runtime/"webbie-speaking"
        self.voice=voice
        self.offline=offline
        self._lock=threading.RLock()
        self._worker=None
        self._event=None
        self._process=None

    def is_speaking(self):
        with self._lock:
            return self._worker is not None and self._worker.is_alive()

    def _halt_process(self,proc):
        if not proc or proc.poll() is not None:
            return
        try:
            os.killpg(proc.pid,signal.SIGTERM)
        except (OSError,ProcessLookupError):
            try:
                proc.terminate()
            except OSError:
                pass

    def stop(self):
        with self._lock:
            worker=self._worker
            event=self._event
            proc=self._process
            if event:
                event.set()
            self._halt_process(proc)
        if worker and worker is not threading.current_thread():
            worker.join(timeout=1.5)
        with self._lock:
            return not (self._worker and self._worker.is_alive())

    def _run_process(self, command, event, timeout):
        proc=None
        try:
            proc=subprocess.Popen(command,stdout=subprocess.DEVNULL,
                                  stderr=subprocess.DEVNULL,start_new_session=True)
            with self._lock:
                self._process=proc
            deadline=time.monotonic()+timeout
            while proc.poll() is None:
                if event.is_set() or time.monotonic()>=deadline:
                    self._halt_process(proc)
                    try:
                        proc.wait(timeout=1)
                    except subprocess.TimeoutExpired:
                        proc.kill()
                        proc.wait()
                    return False
                event.wait(.12)
            return proc.returncode==0 and not event.is_set()
        except (OSError,ValueError):
            return False
        finally:
            with self._lock:
                if self._process is proc:
                    self._process=None

    def _run(self,text,event):
        audio_path=None
        try:
            edge=next((p for p in (
                "/opt/spider-webbie/bin/edge-tts",
                "/usr/local/bin/edge-tts",
                shutil.which("edge-tts")
            ) if p and Path(p).is_file()),None)
            mpv=shutil.which("mpv")
            if edge and mpv and not event.is_set():
                with tempfile.NamedTemporaryFile(prefix="webbie-tts-",suffix=".mp3",delete=False) as temp:
                    audio_path=temp.name
                made=self._run_process([edge,"--voice",self.voice,"--text",text,
                                        "--write-media",audio_path],event,60)
                if made and not event.is_set() and os.path.getsize(audio_path)>0:
                    if self._run_process([mpv,"--no-video","--really-quiet",audio_path],event,120):
                        return
            espeak=shutil.which("espeak-ng")
            if espeak and not event.is_set():
                self._run_process([espeak,"-v",self.offline,"-s","165",text],event,120)
        finally:
            if audio_path:
                try:
                    os.unlink(audio_path)
                except OSError:
                    pass
            with self._lock:
                if self._event is event:
                    try:
                        self.marker.unlink(missing_ok=True)
                    except OSError:
                        pass
                    self._event=None
                    self._worker=None

    def start(self,text):
        text=speakable(text)
        if not text:
            return False
        if not self.stop():
            return False
        with self._lock:
            event=threading.Event()
            self.marker.parent.mkdir(parents=True,exist_ok=True)
            self.marker.write_text("speaking",encoding="utf-8")
            self._event=event
            worker=threading.Thread(target=self._run,args=(text,event),
                                    name="webbie-tts",daemon=True)
            self._worker=worker
            worker.start()
        return True

speech_controller=SpeechController()

def speak(text):
    """Legacy blocking entry point. New Webbie agent should call start()."""
    speech_controller.start(text)
    with speech_controller._lock:
        worker=speech_controller._worker
    if worker:
        worker.join()

if __name__=="__main__":
    import sys
    speak(" ".join(sys.argv[1:]) or "Webbie voice online.")
