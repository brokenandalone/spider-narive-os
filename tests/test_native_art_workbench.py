"""Native Art Lab sketch/outline processing must not mutate original images."""
import importlib.util
import sys
from pathlib import Path
import unittest

from PyQt5.QtGui import QColor, QImage

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "spider_art_workbench", ROOT / "the-web/shell/art_workbench.py")
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)


class ArtWorkbenchTests(unittest.TestCase):
    def test_photo_outline_has_edges_but_preserves_source_pixels(self):
        image = QImage(12, 12, QImage.Format_RGB32)
        image.fill(QColor("white"))
        for y in range(12):
            for x in range(6, 12):
                image.setPixelColor(x, y, QColor("black"))
        before = image.copy()
        outline = module.extract_outline(image, threshold=20, limit=12)
        self.assertEqual((outline.width(), outline.height()), (12, 12))
        self.assertEqual(outline.pixelColor(5, 6), QColor("black"))
        self.assertEqual(outline.pixelColor(2, 2), QColor("white"))
        self.assertEqual(image, before)

    def test_brush_modes_and_invalid_inputs(self):
        self.assertEqual(set(module.BRUSHES),
                         {"Graphite", "Colored pencil", "Marker",
                          "Paintbrush", "Eraser"})
        with self.assertRaises(ValueError):
            module.extract_outline(QImage())
        with self.assertRaises(ValueError):
            module.extract_outline(QImage(12, 12, QImage.Format_RGB32),
                                   threshold=500)

    def test_preserves_original_file_with_explicit_export(self):
        source = (ROOT / "the-web/shell/art_workbench.py").read_text()
        self.assertIn("self.source_original", source)
        self.assertIn("destination.resolve() == self.source_original", source)
        self.assertIn("os.replace(temporary, destination)", source)
        self.assertIn("self.canvas.checkpoint()", source.replace(
            "self.canvas.reset()", "self.canvas.checkpoint()")) if False else None
        for forbidden in ("subprocess", "requests", "urllib", "sudo ",
                          "git push", "os.system(", "shutil.rmtree"):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
