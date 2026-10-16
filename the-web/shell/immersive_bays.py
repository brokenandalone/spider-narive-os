"""Immersive visual work surfaces inside the existing Spider OS workspace tabs.

Source-stage only. This module never changes KDE settings, user projects,
the Webbie service, installed models, or source files. Canvas animations are
decorative; local file selection is deliberate and read-only.
"""
from __future__ import annotations

import math
import struct
import wave
from pathlib import Path

from PyQt5.QtCore import Qt, QRectF, QTimer, pyqtSignal
from PyQt5.QtGui import QColor, QFont, QLinearGradient, QPainter, QPainterPath, QPen, QPixmap
try:
    from PyQt5.QtSvg import QSvgRenderer
except ImportError:
    QSvgRenderer = None

try:
    from app_visuals import app_art
except ImportError:
    app_art = None

from PyQt5.QtWidgets import (
    QFileDialog, QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget,
)

SCENES = {
    "studio": ("RECORDING FLOOR", "TRACKS / CONSOLE / MIX", "#b54175",
               ("Drums", "Bass", "Guitars", "Vocals", "Piano", "FX")),
    "author": ("THE BROKEN WORLD", "BLACK RAIN / CITY ATLAS", "#bd3345",
               ("Apartment 17", "Mercer & Ninth", "City Hall",
                "Platform Six", "House of Echoes")),
    "study": ("THE LEARNING CAMPUS", "COURSES / PROJECTS / RESEARCH", "#32abd8",
              ("Coursework", "Research", "Milestones", "Revision")),
    "kali-bay": ("CYBER OPERATIONS", "LAB / EVIDENCE / SAFETY", "#18ba9d",
                 ("Lab", "Forensics", "Evidence", "Reports")),
    "media": ("SPIDER CINEMA", "THEATER / LIBRARY / VISUALIZER", "#d88742",
              ("Films", "Music", "Radio", "Photos")),
    "webbie": ("WEBBIE INTELLIGENCE", "RESEARCH / MEMORY / CONTROL", "#a578fa",
               ("Research", "Knowledge", "Tasks", "Privacy")),
    "deep-forage": ("THE DEEP FORAGE", "EVIDENCE / SOURCES / CONNECTIONS", "#8e84f9",
                    ("Evidence", "Connections", "Research", "Review")),
    "art-lab": ("ART LAB", "CANVAS / ASSETS / PRODUCTION", "#e58caf",
                ("Artwork", "References", "Wallpapers", "Exports")),
}

AUTHOR_POINTS = (
    ("Apartment 17", 0.19, 0.37), ("Mercer & Ninth", 0.38, 0.59),
    ("City Hall", 0.59, 0.31), ("Platform Six", 0.77, 0.64),
    ("House of Echoes", 0.88, 0.21),
)


class BayCanvas(QWidget):
    """Animated visual surface; never simulates completed external actions."""

    selected = pyqtSignal(str)

    def __init__(self, workspace, parent=None):
        super().__init__(parent)
        self.workspace = workspace
        artwork = app_art(Path(__file__).resolve().parents[2], workspace, "backgrounds") if app_art is not None else None
        self.svg_background = QSvgRenderer(str(artwork)) if (QSvgRenderer is not None and artwork) else None
        self.frame = 0
        self.selected_name = ""
        self.media_image = QPixmap()
        self.samples = []
        self.setMinimumHeight(165)
        self.setAccessibleName("Spider OS immersive " + workspace + " scene")
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.advance)
        self.timer.start(80)

    def advance(self):
        if self.isVisible():
            self.frame = (self.frame + 1) % 3600
            self.update()

    def mousePressEvent(self, event):
        if self.workspace == "author":
            x = event.pos().x() / max(1, self.width())
            y = event.pos().y() / max(1, self.height())
            closest = min(AUTHOR_POINTS, key=lambda p: (x - p[1])**2 + (y - p[2])**2)
            if (x - closest[1])**2 + (y - closest[2])**2 < 0.035:
                self.selected_name = closest[0]
                self.selected.emit(self.selected_name)
                self.update()
                return
        super().mousePressEvent(event)

    def _grid(self, painter, w, h, accent):
        painter.setPen(QPen(QColor(accent).darker(180), 1))
        for x in range(0, w, 38):
            painter.drawLine(x, 0, x, h)
        for y in range(0, h, 27):
            painter.drawLine(0, y, w, y)

    def _text(self, painter, x, y, txt, color="#eceaf6", size=10):
        painter.setPen(QColor(color))
        painter.setFont(QFont("Sans Serif", size, QFont.DemiBold))
        painter.drawText(int(x), int(y), str(txt))

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        if w < 2 or h < 2:
            painter.end()
            return
        title, subtitle, accent, labels = SCENES[self.workspace]
        bg = QLinearGradient(0, 0, w, h)
        bg.setColorAt(0, QColor("#090c1b" if self.workspace != "author" else "#0e080c"))
        bg.setColorAt(1, QColor(accent).darker(440))
        if self.svg_background is not None and self.svg_background.isValid():
            self.svg_background.render(painter, QRectF(0, 0, w, h))
            painter.fillRect(self.rect(), QColor(10, 7, 19, 144))
        else:
            painter.fillRect(self.rect(), bg)
        self._grid(painter, w, h, accent)
        if self.workspace == "studio":
            for row, name in enumerate(labels):
                top = 18 + row * (h - 30) / len(labels)
                painter.fillRect(QRectF(18, top, w - 36, 18), QColor("#19152b"))
                self._text(painter, 24, top + 13, name, size=9)
                painter.setPen(QPen(QColor(accent), 1.5))
                path = QPainterPath()
                base = top + 9
                for index in range(220):
                    x = 125 + index * max(0, w - 160) / 220
                    sample = (self.samples[index % len(self.samples)] if self.samples
                              else math.sin(index * .18 + row) * math.sin(index * .07))
                    y = base + sample * 6
                    if index == 0: path.moveTo(x, y)
                    else: path.lineTo(x, y)
                painter.drawPath(path)
            self._text(painter, max(0, w - 210), h - 6,
                       "SELECT A WAV FOR REAL WAVEFORM" if not self.samples else "WAV SOURCE INSPECTED",
                       "#cdaac1", 8)
        elif self.workspace == "author":
            painter.setPen(Qt.NoPen)
            for i in range(23):
                x = i * w / 22 - 15
                bh = 28 + ((i * 41) % 100)
                painter.fillRect(QRectF(x, h - bh, w / 20, bh), QColor("#241a23"))
                for j in range(2):
                    painter.fillRect(QRectF(x + 7 + j * 13, h - bh + 13,
                                            3, 5), QColor("#99353b"))
            painter.setPen(QPen(QColor("#766273"), 1))
            for i in range(95):
                x = (i * 47 + self.frame * (1 + i % 3)) % max(1, w)
                y = (i * 31 + self.frame * 4) % max(1, h)
                painter.drawLine(int(x), int(y), int(x - 7), int(y + 12))
            for name, px, py in AUTHOR_POINTS:
                x, y = w * px, h * py
                active = name == self.selected_name
                painter.setPen(QPen(QColor("#fa677b" if active else "#b75367"), 2))
                painter.setBrush(QColor("#df344f" if active else "#49232b"))
                painter.drawEllipse(QRectF(x - 6, y - 6, 12, 12))
                self._text(painter, x + 8, y - 7, name, "#fff0f1", 8)
        elif self.workspace == "media":
            frame = QRectF(w*.12, h*.12, w*.76, h*.65)
            painter.setPen(QPen(QColor(accent), 3))
            painter.setBrush(QColor("#080c1a"))
            painter.drawRoundedRect(frame, 10, 10)
            if not self.media_image.isNull():
                pic = self.media_image.scaled(int(frame.width())-8, int(frame.height())-8,
                                              Qt.KeepAspectRatio, Qt.SmoothTransformation)
                painter.drawPixmap(int(frame.center().x() - pic.width()/2),
                                   int(frame.center().y() - pic.height()/2), pic)
            else:
                for i in range(32):
                    x = w*.17 + i * w*.66/32
                    wave_height = 7 + abs(math.sin(i*.49 + self.frame*.09)) * h*.34
                    painter.fillRect(QRectF(x, h*.44-wave_height*.5,
                                             max(2, w*.66/45), wave_height), QColor(accent))
            self._text(painter, 28, h-10, "CINEMA VISUAL PREVIEW · MEDIA ENGINE UNCHANGED",
                       "#edb888", 9)
        elif self.workspace == "webbie":
            cx, cy = w*.5, h*.48
            for j in range(5, 0, -1):
                rad = 23 + j * 22 + 2 * math.sin(self.frame * .07 + j)
                painter.setPen(QPen(QColor(accent).lighter(90 + 7 * j), 1))
                painter.setBrush(Qt.NoBrush)
                painter.drawEllipse(QRectF(cx - rad, cy - rad, rad*2, rad*2))
            painter.setBrush(QColor("#c49dfd"))
            painter.drawEllipse(QRectF(cx-16, cy-16, 32, 32))
            self._text(painter, 20, h-12, "VISUAL AVATAR · LIVE RESIDENT WEBBIE REMAINS SEPARATE",
                       "#d7b6ff", 9)
        elif self.workspace == "deep-forage":
            coords = [(0.13,.43),(.26,.22),(.37,.57),(.51,.3),(.63,.59),(.76,.25),(.88,.50)]
            painter.setPen(QPen(QColor(accent), 2))
            for i, j in [(0,1),(1,2),(2,3),(3,4),(4,5),(5,6),(1,3),(3,5)]:
                painter.drawLine(int(coords[i][0]*w),int(coords[i][1]*h),
                                 int(coords[j][0]*w),int(coords[j][1]*h))
            for i, (x,y) in enumerate(coords):
                painter.setBrush(QColor("#3a315e"))
                painter.drawEllipse(QRectF(x*w-10, y*h-10, 20, 20))
                self._text(painter, x*w+12,y*h-9,f"EVIDENCE {i+1}", "#d3cbff", 8)
            self._text(painter, 20, h-10, "TOPOLOGY CONCEPT · NOT VERIFIED SOURCE LINKS",
                       "#d3cbff", 8)
        elif self.workspace == "kali-bay":
            cx, cy = w*.56, h*.51
            painter.setPen(QPen(QColor(accent), 1))
            for radius in [25,53,84,113]:
                painter.drawEllipse(QRectF(cx-radius,cy-radius, radius*2,radius*2))
            theta = self.frame*.05
            painter.setPen(QPen(QColor("#46fbd3"),3))
            painter.drawLine(int(cx),int(cy),int(cx+112*math.cos(theta)),
                             int(cy+112*math.sin(theta)))
            for i, label in enumerate(labels):
                self._text(painter, 20, 24+i*24, label.upper()+" / WAITING",
                           "#a4e8d9", 9)
        elif self.workspace == "study":
            for i, label in enumerate(labels):
                x = 26 + i * (w-45)/len(labels)
                box = QRectF(x, 30+(i%2)*19, (w-65)/len(labels), h*.56)
                painter.setBrush(QColor("#11314b"))
                painter.setPen(QPen(QColor(accent), 2))
                painter.drawRoundedRect(box, 8, 8)
                self._text(painter, x+7, box.bottom()-15, label.upper(),
                           "#bfeaff", 9)
            self._text(painter, 26,h-8, "COURSEWORK REMAINS IN THE NATIVE STUDY WINDOW",
                       "#bfeaff", 9)
        elif self.workspace == "art-lab":
            for i, label in enumerate(labels[:3]):
                box = QRectF(25 + i*w*.29, 18+(i%2)*12,w*.24,h*.68)
                painter.setBrush(QColor(["#40203b","#27344c","#503347"][i]))
                painter.setPen(QPen(QColor(accent),2))
                painter.drawRoundedRect(box, 6, 6)
                if i == 0 and not self.media_image.isNull():
                    pic = self.media_image.scaled(int(box.width())-8,int(box.height())-8,
                                                  Qt.KeepAspectRatio,Qt.SmoothTransformation)
                    painter.drawPixmap(int(box.center().x()-pic.width()/2),
                                       int(box.center().y()-pic.height()/2),pic)
                else:
                    painter.setBrush(QColor(["#ae648f","#6daecc","#e2a37e"][i]))
                    painter.drawEllipse(QRectF(box.center().x()-20,box.center().y()-28,40,56))
                self._text(painter, box.x()+5,box.bottom()-9,label.upper(), "#fff0fc", 8)
        painter.end()


def _read_wav_preview(path):
    """Bounded, read-only PCM sample preview, not playback or DAW processing."""
    result = []
    with wave.open(str(path), "rb") as wav:
        width = wav.getsampwidth()
        channels = wav.getnchannels()
        frames = wav.getnframes()
        if width not in (1, 2, 4) or channels < 1 or channels > 16:
            raise ValueError("Unsupported uncompressed PCM WAV format")
        # Read one short frame per sample; no full file load.
        for i in range(220):
            wav.setpos(min(frames - 1, int(i * frames / 220)))
            chunk = wav.readframes(1)
            if len(chunk) < width:
                break
            if width == 1: amp = (chunk[0]-128)/128.
            elif width == 2: amp = struct.unpack_from("<h",chunk)[0]/32768.
            else: amp = struct.unpack_from("<i",chunk)[0]/2147483648.
            result.append(amp)
    return result


class ImmersiveBay(QWidget):
    """Attached to an existing native bay, not a replacement application."""

    def __init__(self, workspace, parent=None):
        super().__init__(parent)
        if workspace not in SCENES:
            raise ValueError("Not an immersive workspace")
        self.workspace = workspace
        self.setObjectName("spiderNativeImmersiveBay")
        self.setProperty("bay", workspace)
        self.setStyleSheet(
            "QWidget#spiderNativeImmersiveBay {background:#100c1b;"
            "border:1px solid #6e477f;border-radius:12px;}"
            "QLabel {color:#efe7fa;} QPushButton {padding:6px 12px;}")
        self.setMaximumHeight(285)
        layout = QVBoxLayout(self)
        heading = QHBoxLayout()
        title, tagline, accent, _ = SCENES[workspace]
        name = QLabel(title + "  /  " + tagline)
        name.setAccessibleName("Immersive bay " + title)
        name.setStyleSheet("font-weight:bold;color:" + accent + ";")
        heading.addWidget(name, 1)
        self.expand = QPushButton("Expand scene")
        self.expand.clicked.connect(self.toggle_expanded)
        heading.addWidget(self.expand)
        layout.addLayout(heading)
        self.canvas = BayCanvas(workspace, self)
        self.canvas.selected.connect(self.select_location)
        layout.addWidget(self.canvas, 1)
        row = QHBoxLayout()
        self.status = QLabel("Existing native workspace remains below this scene.")
        self.status.setWordWrap(True)
        row.addWidget(self.status, 1)
        if workspace in ("studio","media","art-lab"):
            choose = QPushButton("Inspect local file (read only)")
            choose.clicked.connect(self.choose_file)
            row.addWidget(choose)
        layout.addLayout(row)

    def select_location(self, location):
        # Read-only scene selection; no manuscript/canon mutation.
        self.status.setText(location + " selected in visual Atlas. Open Author below to edit.")

    def toggle_expanded(self):
        expanded = self.maximumHeight() < 600
        self.setMaximumHeight(680 if expanded else 285)
        self.canvas.setMinimumHeight(420 if expanded else 165)
        self.expand.setText("Compact scene" if expanded else "Expand scene")

    def choose_file(self):
        kind = self.workspace
        if kind == "studio":
            filename, _ = QFileDialog.getOpenFileName(
                self,"Inspect WAV","", "WAV audio (*.wav)")
        elif kind == "art-lab":
            filename, _ = QFileDialog.getOpenFileName(
                self,"Preview artwork","", "Images (*.png *.jpg *.jpeg *.webp)")
        else:
            filename, _ = QFileDialog.getOpenFileName(
                self,"Preview media artwork","", "Images (*.png *.jpg *.jpeg *.webp)")
        if not filename:
            return
        try:
            if kind == "studio":
                self.canvas.samples = _read_wav_preview(filename)
            else:
                pic = QPixmap(filename)
                if pic.isNull():
                    raise ValueError("Image could not be read")
                self.canvas.media_image = pic
            self.canvas.update()
            self.status.setText("Previewing (read only): " + Path(filename).name)
        except (OSError, EOFError, ValueError, wave.Error) as exc:
            self.status.setText("Preview unavailable: " + str(exc))
