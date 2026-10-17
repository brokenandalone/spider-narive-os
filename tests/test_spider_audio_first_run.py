"""Real welcome and beta audio engine acceptance without launching a microphone."""
import os
os.environ.setdefault("QT_QPA_PLATFORM","offscreen")
import unittest
from unittest.mock import patch


class StudioFirstProjectExperience(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            from PyQt5.QtWidgets import QApplication
        except ImportError:
            raise unittest.SkipTest("PyQt5 not installed")
        cls.app=QApplication.instance() or QApplication([])

    def test_all_first_run_buttons_open_real_native_studio_tools(self):
        from studio.main import SpiderStudio
        window=SpiderStudio()
        try:
            self.assertIs(
                window.tool_tabs.currentWidget(),window.welcome_panel)
            buttons=window.welcome_panel.actions
            self.assertEqual(len(buttons),5)
            buttons["Import tracks · Start a song"].click()
            self.assertIs(
                window.tool_tabs.currentWidget(),window.stem_import_panel)
            buttons["Record a new take"].click()
            self.assertIs(
                window.tool_tabs.currentWidget(),window.audio_capture_page)
            buttons["Play instruments"].click()
            self.assertIs(
                window.tool_tabs.currentWidget(),window.instrument_page)
            class FakeMixer:
                created=0
                opened=0
                def __init__(self,parent=None):
                    FakeMixer.created+=1
                    self.parent=parent
                def exec_(self):
                    FakeMixer.opened+=1
                    return 0
            with patch("studio.session_mix_dialog.SessionMixDialog",FakeMixer):
                buttons["Open an existing song"].click()
            self.assertEqual((FakeMixer.created,FakeMixer.opened),(1,1))
            class FakeSongs:
                shown=0
                def __init__(self,parent=None):
                    pass
                def exec_(self):
                    FakeSongs.shown+=1
                    return 0
            with patch("studio.saved_songs_dialog.SavedSongsDialog",FakeSongs):
                buttons["Recent saved songs"].click()
            self.assertEqual(FakeSongs.shown,1)
            self.assertFalse(window.stem_import_panel.items)
        finally:
            window.close()

if __name__=="__main__":
    unittest.main()
