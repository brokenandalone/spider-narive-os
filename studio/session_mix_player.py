"""Play rendered Spider Audio Studio mixes IN the session mixer.

This transport is intentionally independent of recording and FFmpeg. It only
plays a finished regular local WAV AFTER explicit owner action. If QtMultimedia
is absent or its platform backend fails, the existing external-player button
remains usable. It never opens input devices or changes audio sources.
"""
from __future__ import annotations
from pathlib import Path
from PyQt5.QtCore import Qt,QUrl
from PyQt5.QtWidgets import QWidget,QHBoxLayout,QLabel,QPushButton,QSlider
try:
    from PyQt5.QtMultimedia import QMediaPlayer,QMediaContent
except ImportError:
    QMediaPlayer=None
    QMediaContent=None


def nice_time(ms):
    if type(ms) is not int or ms<0:
        return "0:00"
    seconds=ms//1000
    return f"{seconds//60}:{seconds%60:02d}"


class MixPlaybackBar(QWidget):
    """Owner-controlled seek/pause/stop for an exported finished stereo WAV."""
    def __init__(self,parent=None):
        super().__init__(parent)
        self.setObjectName("spiderMixPlayback")
        self.file=None
        self.player=None
        self._seeking=False
        layout=QHBoxLayout(self)
        layout.setContentsMargins(0,3,0,3)
        self.play_button=QPushButton("▶ Play in Studio")
        self.pause_button=QPushButton("⏸ Pause")
        self.stop_button=QPushButton("■ Stop")
        for widget in (self.play_button,self.pause_button,self.stop_button):
            widget.setEnabled(False)
            layout.addWidget(widget)
        self.seek=QSlider(Qt.Horizontal)
        self.seek.setAccessibleName("Position in rendered guitar song")
        self.seek.setRange(0,0)
        self.seek.setEnabled(False)
        layout.addWidget(self.seek,1)
        self.elapsed=QLabel("0:00 / 0:00")
        layout.addWidget(self.elapsed)
        self.status=QLabel("Render or open a mix to enable playback.")
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        if QMediaPlayer is not None:
            try:
                self.player=QMediaPlayer(self)
                self.player.setVolume(80)
                self.player.positionChanged.connect(self._position)
                self.player.durationChanged.connect(self._duration)
                self.player.stateChanged.connect(self._state)
                self.player.error.connect(self._error)
                self.play_button.clicked.connect(self.play)
                self.pause_button.clicked.connect(self.pause)
                self.stop_button.clicked.connect(self.stop)
                self.seek.sliderPressed.connect(self._seek_start)
                self.seek.sliderReleased.connect(self._seek_finish)
            except (RuntimeError,TypeError,AttributeError) as error:
                self.player=None
                self.status.setText("Qt audio output is unavailable: "+str(error)[:110])
        if self.player is None:
            self.status.setText(
                "Internal playback backend is unavailable. "
                "Use 'Listen to last rendered WAV' to open the system audio player.")

    def load(self,path):
        source=Path(path).expanduser()
        if source.is_symlink() or source.suffix.lower()!=".wav" or not source.is_file():
            self.clear()
            self.status.setText("Choose a finished, regular rendered WAV.")
            return False
        self.file=source
        if self.player is None:
            self.status.setText("Open the finished WAV in your system player.")
            return False
        self.player.stop()
        self.player.setMedia(QMediaContent(QUrl.fromLocalFile(str(source))))
        self.seek.setValue(0)
        self.elapsed.setText("0:00 / 0:00")
        self.play_button.setEnabled(True)
        self.pause_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.seek.setEnabled(True)
        self.status.setText("Ready: "+source.name)
        return True

    def clear(self):
        if self.player is not None:
            self.player.stop()
            self.player.setMedia(QMediaContent())
        self.file=None
        for button in (self.play_button,self.pause_button,self.stop_button,self.seek):
            button.setEnabled(False)
        self.seek.setRange(0,0)
        self.elapsed.setText("0:00 / 0:00")

    def play(self):
        if self.player is not None and self.file is not None and self.file.is_file():
            self.player.play()
            self.status.setText("Playing: "+self.file.name)

    def pause(self):
        if self.player is not None:
            self.player.pause()
            self.status.setText("Playback paused.")

    def stop(self):
        if self.player is not None:
            self.player.stop()
            self.status.setText("Playback stopped.")

    def _state(self,state):
        if self.player is None:return
        active=state==QMediaPlayer.PlayingState
        self.play_button.setEnabled(not active and self.file is not None)
        self.pause_button.setEnabled(active)

    def _position(self,ms):
        if not self._seeking:
            self.seek.setValue(max(0,min(self.seek.maximum(),int(ms))))
        duration=self.player.duration() if self.player is not None else 0
        self.elapsed.setText(nice_time(int(ms))+" / "+nice_time(max(0,int(duration))))

    def _duration(self,ms):
        self.seek.setRange(0,max(0,int(ms)))

    def _seek_start(self):
        self._seeking=True

    def _seek_finish(self):
        self._seeking=False
        if self.player is not None:
            self.player.setPosition(self.seek.value())

    def _error(self,*args):
        if self.player is None:return
        self.status.setText(
            "Internal audio output failed: "+self.player.errorString()[:180]+
            ". Use the system-player button if necessary.")
        self.play_button.setEnabled(False)

    def shutdown(self):
        self.clear()
