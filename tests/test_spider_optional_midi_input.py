"""MIDI input must never access devices until the owner explicitly connects."""
import os
import unittest
from unittest.mock import patch
from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_ACCESSIBILITY", "0")

try:
    from PyQt5.QtWidgets import QApplication
    from studio import midi_input_panel as midi_panel
except ImportError:
    QApplication = None

@unittest.skipUnless(QApplication, "PyQt5 unavailable")
class MidiInputTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_missing_dependency_is_safe_and_no_devices_open(self):
        with patch.object(midi_panel, "mido", None):
            self.assertEqual(midi_panel.midi_input_names(), [])
            received = []
            panel = midi_panel.MidiInputPanel(lambda *args: received.append(args))
            try:
                self.assertFalse(panel.connect_button.isEnabled())
                panel._note(60, 91)
                self.assertEqual(received, [("keys", 60, 91)])
                panel.instrument.setCurrentIndex(1)
                panel._note(40, 100)
                self.assertEqual(received[-1], ("guitar", 40, 100))
                panel._note(100, 100)
                self.assertEqual(len(received), 2)  # synth's MIDI pitch bounds
            finally:
                panel.close()

    def test_refresh_lists_ports_but_never_opens_them(self):
        counter = {"opened": 0}
        def opened(*args, **kwargs):
            counter["opened"] += 1
            raise AssertionError("MIDI port was accessed without permission")
        fake = SimpleNamespace(get_input_names=lambda: ["Controller A"], open_input=opened)
        with patch.object(midi_panel, "mido", fake):
            panel = midi_panel.MidiInputPanel(lambda *args: None)
            try:
                self.assertEqual(panel.device.count(), 1)
                self.assertTrue(panel.connect_button.isEnabled())
                self.assertEqual(counter["opened"], 0)
            finally:
                panel.close()

if __name__ == "__main__":
    unittest.main()
