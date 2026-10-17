"""Nonblocking, bounded taskbar volume control for existing PipeWire/WirePlumber."""
import re
import shutil
import subprocess
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtWidgets import QWidget, QHBoxLayout, QLabel, QPushButton, QSlider, QVBoxLayout

def volume_state():
    tool = shutil.which('wpctl')
    if not tool:
        return None, False
    try:
        result = subprocess.run([tool, 'get-volume', '@DEFAULT_AUDIO_SINK@'],
                                capture_output=True, text=True, timeout=2, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return None, False
    if result.returncode:
        return None, False
    match = re.search(r'Volume:\s*([0-9]+(?:\.[0-9]+)?)', result.stdout)
    if not match:
        return None, False
    return max(0, min(100, round(float(match.group(1)) * 100))), '[MUTED]' in result.stdout

def set_volume_percent(value):
    if type(value) is not int or not 0 <= value <= 100:
        raise ValueError('Volume must be an integer from 0 to 100')
    _set(['set-volume', '--limit', '1.0', '@DEFAULT_AUDIO_SINK@', str(value) + '%'])

def toggle_mute():
    _set(['set-mute', '@DEFAULT_AUDIO_SINK@', 'toggle'])

def _set(args):
    tool = shutil.which('wpctl')
    if not tool:
        raise RuntimeError('WirePlumber is not available')
    try:
        result = subprocess.run([tool, *args], timeout=3, capture_output=True, check=False)
    except (OSError, subprocess.TimeoutExpired) as error:
        raise RuntimeError('Audio service did not respond') from error
    if result.returncode:
        raise RuntimeError('Could not change default output volume')

class VolumeWorker(QThread):
    result = pyqtSignal(object)
    error = pyqtSignal(str)
    def __init__(self, value=None, mute=False, parent=None):
        super().__init__(parent); self.value=value; self.mute=mute
    def run(self):
        try:
            if self.mute: toggle_mute()
            elif self.value is not None: set_volume_percent(self.value)
            self.result.emit(volume_state())
        except (OSError, ValueError, RuntimeError) as error:
            self.error.emit(str(error))

class VolumePanel(QWidget):
    """One compact desktop control, never blocks the Qt event loop."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Spider OS Volume')
        layout = QVBoxLayout(self)
        self.status = QLabel('Checking output volume…'); layout.addWidget(self.status)
        controls=QHBoxLayout(); layout.addLayout(controls)
        self.slider=QSlider(Qt.Horizontal); self.slider.setRange(0,100)
        self.slider.setAccessibleName('Output volume percentage')
        controls.addWidget(self.slider)
        self.mute=QPushButton('Mute / Unmute'); controls.addWidget(self.mute)
        self.slider.sliderReleased.connect(self.change)
        self.mute.clicked.connect(self.switch_mute)
        self.worker=None
        self._available=False
        self.refresh()

    def refresh(self):
        # Even a read-only wpctl call can stall for two seconds on a broken
        # sound service. Run ALL volume commands off the Qt GUI event loop.
        self._run()

    def _render_state(self, state):
        level, muted=state
        self._available=level is not None
        if not self._available:
            self.status.setText('Audio unavailable. Check PipeWire and WirePlumber.')
            return
        self.slider.setValue(level)
        self.status.setText(f'Output: {level}%' + (' · Muted' if muted else ''))

    def change(self):
        self._run(value=self.slider.value())

    def switch_mute(self):
        self._run(mute=True)

    def _failed(self, error):
        self._available=False
        self.status.setText(error)

    def _finished(self):
        self.slider.setEnabled(self._available)
        self.mute.setEnabled(self._available)

    def _run(self, value=None, mute=False):
        if self.worker and self.worker.isRunning(): return
        self.slider.setEnabled(False); self.mute.setEnabled(False)
        self.worker=VolumeWorker(value=value,mute=mute,parent=self)
        self.worker.result.connect(self._render_state)
        self.worker.error.connect(self._failed)
        self.worker.finished.connect(self._finished)
        self.worker.start()

    def closeEvent(self, event):
        if self.worker and self.worker.isRunning():
            event.ignore()
        else:
            event.accept()
