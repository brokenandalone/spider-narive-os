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
RUNTIME_DIR = Path(os.environ.get("XDG_RUNTIME_DIR", f"/run/user/{os.getuid()}")) / "spider-os"
NARRATING_MARKER = RUNTIME_DIR / "webbie-narrating"
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


def book_reading_plan(chapters):
    """Return ordered (title, spoken text, chapter_id, section index) entries."""
    items = []
    for chapter in chapters:
        title = str(chapter["title"])
        ident = int(chapter["id"])
        items.append((title, title, ident, 0))
        for index, part in enumerate(speech_segments(chapter["content"]), 1):
            items.append((title, part, ident, index))
    return items


class WebbieReader(QThread):
    changed = pyqtSignal(str)
    positionChanged = pyqtSignal(int, int, int)
    bookCompleted = pyqtSignal(int)

    def __init__(self, parent=None, voice_script=WEBBIE_VOICE):
        super().__init__(parent)
        self.voice_script = Path(voice_script)
        self.queue = []
        self._book_id = None
        self._stop_flag = threading.Event()
        self._go = threading.Event()
        self._go.set()
        self._lock = threading.Lock()
        self._process = None

    def available(self):
        return self.voice_script.is_file()

    def start_chapter(self, content, title="Chapter"):
        items = [(str(title), str(title), None, 0)]
        items.extend((str(title), part, None, index) for index, part
                     in enumerate(speech_segments(content), 1))
        self._start_queue(items)

    def start_book(self, chapters, *, book_id=None, resume=None):
        items = book_reading_plan(chapters)
        if resume is not None:
            # Never quietly begin at the wrong chapter if a bookmark is bad.
            matches = [index for index, item in enumerate(items)
                       if (item[2], item[3]) == tuple(resume)]
            if not matches:
                raise ValueError("The saved audiobook position no longer exists.")
            items = items[matches[0]:]
        self._start_queue(items, book_id=book_id)

    def _start_queue(self, items, *, book_id=None):
        if self.isRunning():
            raise RuntimeError("Webbie is already reading. Stop the current reading first.")
        if not self.available():
            raise RuntimeError("Webbie's voice module was not found. Check the Spider OS voice installation.")
        if not items:
            raise ValueError("The selected manuscript has no text to read.")
        self._book_id = int(book_id) if book_id is not None else None
        self.queue = items
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
            RUNTIME_DIR.mkdir(mode=0o700, parents=True, exist_ok=True)
            # The speech listener checks this separate marker to avoid TTS echo.
            # The resident agent owns webbie-speaking; do not overwrite it.
            NARRATING_MARKER.write_text(str(os.getpid()), encoding="ascii")
            os.chmod(NARRATING_MARKER, 0o600)
            total = len(self.queue)
            for index, (chapter, content, chapter_id, section_index) in enumerate(self.queue, 1):
                while not self._go.wait(0.1):
                    if self._stop_flag.is_set():
                        break
                if self._stop_flag.is_set():
                    break
                self.changed.emit(
                    f"Webbie reading {chapter} | section {index} of {total}")
                # Store this section BEFORE speaking it so interruptions
                # replay, rather than silently skip, unfinished audio.
                if self._book_id is not None and chapter_id is not None:
                    self.positionChanged.emit(
                        self._book_id, chapter_id, section_index)
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
            if not self._stop_flag.is_set() and self._book_id is not None:
                self.bookCompleted.emit(self._book_id)
            self.changed.emit(
                "Webbie narration stopped." if self._stop_flag.is_set()
                else "Webbie finished reading.")
        except (OSError, RuntimeError) as error:
            self.changed.emit("Webbie voice error: " + str(error))
        finally:
            try:
                if NARRATING_MARKER.read_text(encoding="ascii").strip() == str(os.getpid()):
                    NARRATING_MARKER.unlink()
            except OSError:
                pass
            with self._lock:
                self._process = None
