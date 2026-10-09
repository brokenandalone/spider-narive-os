"""Local, stoppable read-aloud without network access or Webbie command rights."""
import re
import shutil
from PyQt5.QtCore import QObject, QProcess, pyqtSignal


class LocalReader(QObject):
    changed = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.process = QProcess(self)
        self.process.finished.connect(self.advance)
        self.paragraphs = []
        self.position = 0
        self.voice = shutil.which('espeak-ng') or shutil.which('espeak')
        self.running = False

    def available(self):
        return self.voice is not None

    def start(self, content):
        if not self.voice:
            raise RuntimeError('Read aloud needs espeak-ng or espeak installed.')
        if not isinstance(content, str) or not content.strip():
            raise ValueError('Choose a chapter with text to read.')
        self.stop()
        # Small sentences keep QProcess argv bounded and interruptible.
        self.paragraphs = []
        for paragraph in content.splitlines():
            paragraph = paragraph.strip()
            while paragraph:
                segment = paragraph[:500]
                if len(paragraph) > 500:
                    boundary = max(segment.rfind('. '), segment.rfind('! '), segment.rfind('? '), segment.rfind(' '))
                    if boundary >= 150:
                        segment = paragraph[:boundary+1]
                self.paragraphs.append(segment)
                paragraph = paragraph[len(segment):].strip()
        self.position = 0
        self.running = True
        self.changed.emit('Reading aloud (local system voice)')
        self.advance()

    def advance(self, *args):
        if not self.running:
            return
        if self.position >= len(self.paragraphs):
            self.stop()
            self.changed.emit('Reading complete.')
            return
        paragraph = self.paragraphs[self.position]
        self.position += 1
        self.process.start(self.voice, ['-v', 'en-au', '-s', '140', '--', paragraph])

    def stop(self):
        self.running = False
        if self.process.state() != QProcess.NotRunning:
            self.process.kill()
            self.process.waitForFinished(1000)
        self.paragraphs = []
        self.position = 0
        self.changed.emit('Read aloud stopped.')

