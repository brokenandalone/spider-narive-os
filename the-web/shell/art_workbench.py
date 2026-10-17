"""Non-destructive native Spider Art Lab canvas and photo outline converter.

Simple Qt raster brush workbench; original image files are NEVER edited.
Produces a new PNG only after explicit export. Heavy 3D/layer tools still
belong to installed Krita, GIMP and Blender.
"""
from pathlib import Path
import os
import tempfile
from PyQt5.QtCore import Qt, QPoint, QSize
from PyQt5.QtGui import (QImage, QPainter, QPen, QColor, QPixmap)
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QComboBox,
    QLabel, QPushButton, QSpinBox, QFileDialog, QMessageBox, QColorDialog, QScrollArea)

WIDTH = 1000
HEIGHT = 700
BRUSHES = ("Graphite", "Colored pencil", "Marker", "Paintbrush", "Eraser")


def extract_outline(original, threshold=34, limit=1200):
    """Locally transform a QImage into high-contrast ink outlines.

    Bounded square, independent of camera, disk, model or network access.
    """
    if not isinstance(original, QImage) or original.isNull():
        raise ValueError("Select a readable photo")
    if not isinstance(threshold, int) or not 10 <= threshold <= 120:
        raise ValueError("Outline sensitivity must be 10–120")
    photo = original.convertToFormat(QImage.Format_RGB32)
    photo = photo.scaled(limit, limit, Qt.KeepAspectRatio, Qt.SmoothTransformation)
    width, height = photo.width(), photo.height()
    if width < 2 or height < 2:
        raise ValueError("Image is too small to extract an outline")
    def lum(pixel):
        return (pixel.red() * 299 + pixel.green() * 587 +
                pixel.blue() * 114) // 1000
    ink = QImage(width, height, QImage.Format_ARGB32)
    ink.fill(QColor("white"))
    for y in range(height - 1):
        for x in range(width - 1):
            p = lum(photo.pixelColor(x, y))
            right = lum(photo.pixelColor(x + 1, y))
            below = lum(photo.pixelColor(x, y + 1))
            if abs(p - right) + abs(p - below) >= threshold:
                ink.setPixelColor(x, y, QColor("black"))
    return ink


class DrawingCanvas(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.image = QImage(WIDTH, HEIGHT, QImage.Format_ARGB32)
        self.image.fill(QColor("white"))
        self.brush = "Graphite"
        self.color = QColor("#36313b")
        self.thickness = 4
        self.history = []
        self.drawing = False
        self.last = None
        self.setFixedSize(WIDTH, HEIGHT)
        self.setObjectName("spiderDrawingCanvas")
        self.setMouseTracking(True)
        self.setAccessibleName("Native drawing canvas, brush or eraser")

    def checkpoint(self):
        self.history.append(self.image.copy())
        if len(self.history) > 12:
            self.history.pop(0)

    def undo(self):
        if self.history:
            self.image = self.history.pop()
            self.update()
            return True
        return False

    def reset(self):
        self.checkpoint()
        self.image.fill(QColor("white"))
        self.update()

    def load_outline(self, source):
        result = extract_outline(source)
        self.checkpoint()
        self.image.fill(QColor("white"))
        with_painter = QPainter(self.image)
        with_painter.drawImage(
            self.image.rect(), result, result.rect())
        with_painter.end()
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#e4dfe8"))
        painter.drawImage(0, 0, self.image)
        painter.end()

    def stroke(self, start, end):
        painter = QPainter(self.image)
        color = QColor("white") if self.brush == "Eraser" else QColor(self.color)
        if self.brush == "Graphite":
            color.setAlpha(155)
        elif self.brush == "Colored pencil":
            color.setAlpha(195)
        elif self.brush == "Marker":
            color.setAlpha(185)
        elif self.brush == "Paintbrush":
            color.setAlpha(230)
        width = max(1, self.thickness)
        if self.brush in ("Marker", "Eraser"):
            width *= 3
        pen = QPen(color, width, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(pen)
        painter.drawLine(start, end)
        painter.end()
        self.update()

    def mousePressEvent(self, event):
        if event.button() != Qt.LeftButton:
            return
        self.checkpoint()
        self.drawing = True
        self.last = event.pos()
        self.stroke(self.last, self.last)

    def mouseMoveEvent(self, event):
        if not self.drawing or self.last is None:
            return
        self.stroke(self.last, event.pos())
        self.last = event.pos()

    def mouseReleaseEvent(self, event):
        if event.button() != Qt.LeftButton or not self.drawing:
            return
        self.stroke(self.last, event.pos())
        self.drawing = False
        self.last = None


class ArtWorkbench(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("spiderNativeArtWorkbench")
        self.source_original = None
        root = QVBoxLayout(self)
        title = QLabel("ART LAB / PAINTING & OUTLINE WORKBENCH")
        title.setStyleSheet("font-size:20px;font-weight:bold;color:#e2bcff")
        root.addWidget(title)
        explanation = QLabel(
            "Draw using graphite, colored pencil, marker or paint tools. "
            "Convert an existing photo into an ink outline and add your own strokes. "
            "Original photos are never overwritten, and exporting always requires your choice.")
        explanation.setWordWrap(True)
        root.addWidget(explanation)
        row = QHBoxLayout()
        self.mode = QComboBox()
        self.mode.addItems(BRUSHES)
        row.addWidget(self.mode)
        self.thickness = QSpinBox()
        self.thickness.setRange(1, 28)
        self.thickness.setValue(4)
        row.addWidget(QLabel("Stroke size"))
        row.addWidget(self.thickness)
        color = QPushButton("Choose paint color")
        color.clicked.connect(self.choose_color)
        row.addWidget(color)
        root.addLayout(row)
        tools = QHBoxLayout()
        for text, method in (
                ("Import photo as outline", self.import_photo),
                ("Undo last stroke", self.undo),
                ("Clear (keep undo)", self.clear),
                ("Export new PNG", self.export)):
            button = QPushButton(text)
            button.clicked.connect(method)
            tools.addWidget(button)
        root.addLayout(tools)
        self.canvas = DrawingCanvas(self)
        self.mode.currentTextChanged.connect(
            lambda choice: setattr(self.canvas, "brush", choice))
        self.thickness.valueChanged.connect(
            lambda value: setattr(self.canvas, "thickness", value))
        scroll = QScrollArea()
        scroll.setWidgetResizable(False)
        scroll.setWidget(self.canvas)
        root.addWidget(scroll, 1)
        self.status = QLabel("Canvas ready. Krita, Blender and GIMP remain installed and available.")
        self.status.setWordWrap(True)
        root.addWidget(self.status)

    def choose_color(self):
        choice = QColorDialog.getColor(self.canvas.color, self, "Painting color")
        if choice.isValid():
            self.canvas.color = choice

    def import_photo(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Choose a photo for a new outline", str(Path.home() / "Pictures"),
            "Images (*.png *.jpg *.jpeg *.webp *.bmp)")
        if not path:
            return
        image = QImage(path)
        if image.isNull():
            self.status.setText("Photo was not readable. Canvas unchanged.")
            return
        try:
            self.canvas.load_outline(image)
            self.source_original = Path(path).resolve()
            self.status.setText(
                "Extracted a new outline from " + Path(path).name +
                ". The original photo is untouched.")
        except ValueError as error:
            self.status.setText(str(error))

    def undo(self):
        self.status.setText("Previous canvas restored." if self.canvas.undo()
                            else "No previous stroke to undo.")

    def clear(self):
        if QMessageBox.question(
                self, "Clear canvas?",
                "Clear the canvas? Undo will still restore the previous drawing.",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No) == QMessageBox.Yes:
            self.canvas.reset()
            self.status.setText("Canvas cleared. Use Undo to restore.")

    def export(self):
        selected, _ = QFileDialog.getSaveFileName(
            self, "Export original artwork as a new PNG",
            str(Path.home() / "Pictures" / "spider-art-export.png"),
            "PNG image (*.png)")
        if not selected:
            return
        destination = Path(selected)
        if destination.suffix.lower() != ".png":
            destination = destination.with_suffix(".png")
        if destination.is_symlink():
            self.status.setText("Symlink export target rejected.")
            return
        if self.source_original is not None and destination.resolve() == self.source_original:
            self.status.setText("Original photo is protected. Choose a different export name.")
            return
        if destination.exists() and QMessageBox.question(
                self, "Replace existing PNG?",
                "This destination already exists. Replace that file?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No) != QMessageBox.Yes:
            return
        if not destination.parent.is_dir():
            self.status.setText("Choose an existing export folder.")
            return
        # Export an atomic temporary PNG; the original photo remains protected.
        fd, temporary = tempfile.mkstemp(prefix=".spider-art-", suffix=".png",
                                         dir=destination.parent)
        os.close(fd)
        try:
            if not self.canvas.image.save(temporary, "PNG"):
                raise OSError("Cannot render PNG")
            os.replace(temporary, destination)
            self.status.setText("New PNG exported to " + str(destination))
        except OSError as error:
            self.status.setText("Export failed; canvas intact: " + str(error))
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
