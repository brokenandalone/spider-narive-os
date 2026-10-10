"""Cancelable Author narration using Webbie's existing voice configuration.

Runs the same webbie/voice/tts.py as the resident assistant, so Natasha is
used when available and Webbie's configured offline fallback is retained.
No separate generic Author voice is started.
"""
import os
import signal
import subprocess
import sys
import threading
from pathlib import Path
from PyQt5.QtCore import QThread, pyqtSignal

WEBBIE_VOICE = Path(__file__).resolve().parents[1] / "webbie/voice/tts.py"
VOICE_BOOTSTRAP = (
    "import sys; sys.path.insert(0, sys.argv[1]); "
    "from tts import speak; speak(sys.stdin.read())"
)


def speech_segments(text, limit=440):
    """Return short speech segments in original reading order."""
    if __package__:
        from .review_engine import split_exact
    else:
        from review_engine import split_exact
    result = []
    for paragraph in str(text).splitlines():
        if paragraph.strip():
            result.extend(part.strip() for part in split_exact(paragraph, limit)
                          if part.strip())
    return result


class WebbieReader(QThread):
    changed = pyqtSignal(str)

    def __init__(self, parent=None, voice_script=WEBBIE_VOICE):
        super().__init__(parent)
        self.voice_script = Path(voice_script)
        self.queue = []
        self._stop_flag = threading.Event()
        self._go = threading.Event()
        self._go.set()
        self._lock = threading.Lock()
        self._process = None

    def available(self):
        return self.voice_script.is_file()

    def start_chapter(self, content, title="Chapter"):
        self._start_queue([(str(title), str(content))])

    def start_book(self, chapters):
        self._start_queue([(str(c["title"]), str(c["content"])) for c in chapters])

    def _start_queue(self, chapters):
        if self.isRunning():
            raise RuntimeError("Webbie is already reading. Stop the current reading first.")
        if not self.available():
            raise RuntimeError("Webbie's voice module was not found. Check the Spider OS voice installation.")
        self.queue = []
        for title, content in chapters:
            self.queue.append((title, title))
            self.queue.extend((title, paragraph) for paragraph in speech_segments(content))
        if not self.queue:
            raise ValueError("The selected manuscript has no text to read.")
        self._stop_flag.clear()
        self._go.set()
        super().start()

    def pause(self):
        if self.isRunning():
            self._go.clear()
            self.changed.emit("Pausing after the current spoken section.")

    def resume(self):
        self._go.set()
        if self.isRunning():
            self.changed.emit("Webbie narration resumed.")

    def stop(self):
        self._stop_flag.set()
        self._go.set()
        with self._lock:
            process = self._process
        if process is not None and process.poll() is None:
            self._kill_process_group(process)

    @staticmethod
    def _kill_process_group(process):
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except (ProcessLookupError, OSError):
            pass

    def run(self):
        try:
            total = len(self.queue)
            for index, (chapter, content) in enumerate(self.queue, 1):
                while not self._go.wait(0.1):
                    if self._stop_flag.is_set():
                        break
                if self._stop_flag.is_set():
                    break
                self.changed.emit(
                    f"Webbie reading {chapter} | section {index} of {total}")
                proc = subprocess.Popen(
                    [sys.executable, "-c", VOICE_BOOTSTRAP,
                     str(self.voice_script.parent)],
                    stdin=subprocess.PIPE, stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL, start_new_session=True,
                )
                with self._lock:
                    self._process = proc
                if self._stop_flag.is_set():
                    self._kill_process_group(proc)
                try:
                    proc.communicate(input=content.encode("utf-8"), timeout=175)
                except subprocess.TimeoutExpired:
                    self._kill_process_group(proc)
                    proc.communicate()
                    raise RuntimeError("Webbie narration timed out on a section.")
                finally:
                    with self._lock:
                        if self._process is proc:
                            self._process = None
                if self._stop_flag.is_set():
                    break
                if proc.returncode != 0:
                    raise RuntimeError("Webbie voice stopped unexpectedly.")
            self.changed.emit(
                "Webbie narration stopped." if self._stop_flag.is_set()
                else "Webbie finished reading.")
        except (OSError, RuntimeError) as error:
            self.changed.emit("Webbie voice error: " + str(error))
        finally:
            with self._lock:
                self._process = None
