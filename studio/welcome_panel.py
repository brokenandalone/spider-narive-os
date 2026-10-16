"""Original Spider Studio first-run song dashboard.

Every button leads to an already working native tool, not a launcher stub.
No mic, generator, or recording begins until the owner acts within that tab.
"""
from __future__ import annotations
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QFrame,QGridLayout,QLabel,QPushButton,QVBoxLayout,QWidget
)

class StudioWelcome(QWidget):
    def __init__(self,*,open_import,open_record,open_instruments,open_session,
                 open_recent=None,parent=None):
        super().__init__(parent)
        self.setObjectName("studioWelcome")
        layout=QVBoxLayout(self)
        layout.setContentsMargins(24,22,24,24)
        layout.setSpacing(14)
        headline=QLabel("START SOMETHING WORTH HEARING")
        headline.setStyleSheet(
            "font-size:24px;font-weight:800;color:#c6a8ff")
        layout.addWidget(headline)
        intro=QLabel(
            "Spider Audio Studio brings your recordings and music ideas into "
            "one native production workspace. Your original tracks remain "
            "unchanged when you import and mix.")
        intro.setWordWrap(True)
        layout.addWidget(intro)
        note=QLabel(
            "Choose where to begin. Each option opens a real Studio tool; "
            "nothing records or accesses your microphone automatically.")
        note.setWordWrap(True)
        layout.addWidget(note)
        grid=QGridLayout()
        grid.setSpacing(14)
        items=[
            ("Import tracks · Start a song",
             "Choose guitar, vocal, drum and bass WAV files. Assign roles, "
             "set BPM and create a protected mix session.",open_import),
            ("Record a new take",
             "Choose your microphone or guitar input, record a performance "
             "and build independent multitrack takes.",open_record),
            ("Play instruments",
             "Explore the real instrument workbench, scores, MIDI and "
             "compatible local soundbanks.",open_instruments),
            ("Open an existing song",
             "Reopen a verified session, adjust its channel strips, arrange "
             "regions and render a new finished stereo mix.",open_session),
        ]
        if open_recent is not None:
            items.append((
                "Recent saved songs",
                "Find your latest multitrack recordings by title and tempo, "
                "then verify each track before opening the original mixer.",
                open_recent))

        self.actions={}
        for idx,(title,description,callback) in enumerate(items):
            card=QFrame()
            card.setObjectName("studioWelcomeCard")
            card.setStyleSheet(
                "#studioWelcomeCard {background:#1d162c;"
                "border:1px solid #5d497a;border-radius:12px;}")
            content=QVBoxLayout(card)
            button=QPushButton(title)
            button.setMinimumHeight(55)
            button.setAccessibleName(title)
            button.clicked.connect(
                lambda _checked=False,handler=callback:handler())
            content.addWidget(button)
            detail=QLabel(description)
            detail.setWordWrap(True)
            content.addWidget(detail)
            grid.addWidget(card,idx//2,idx%2)
            self.actions[title]=button
        layout.addLayout(grid)
        information=QLabel(
            "LOCAL AUDIO FIRST • The offline multitrack mixer renders new "
            "48 kHz WAV files. Playback in Studio follows rendering. "
            "Live low-latency monitoring and commercial plugin hosting are "
            "separate features still being validated.")
        information.setWordWrap(True)
        information.setStyleSheet("color:#b6aacb")
        layout.addWidget(information)
        layout.addStretch(1)
