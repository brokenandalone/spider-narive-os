"""One-click starting recipes are deterministic and never replace source stems."""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import unittest

from PyQt5.QtWidgets import QApplication
from studio.mix_presets import PRESET_IDS, PRESETS, preset_mix_values
from studio.band_mix import ROLES
from studio.band_mixer_panel import BandMixerPanel

app = QApplication.instance() or QApplication([])


class MixerPresetTests(unittest.TestCase):
    def test_recipes_have_valid_levels_and_balances(self):
        self.assertEqual(set(PRESET_IDS), {'neutral', 'broken_sorrow', 'duet', 'piano'})
        for key in PRESET_IDS:
            gains, pans = preset_mix_values(key)
            self.assertEqual(set(gains), set(ROLES))
            self.assertEqual(set(pans), set(ROLES))
            self.assertTrue(all(0 <= value <= 2 for value in gains.values()))
            self.assertTrue(all(-1 <= value <= 1 for value in pans.values()))
        heavy_gain, heavy_pan = preset_mix_values('broken_sorrow')
        self.assertLess(heavy_pan['rhythm_guitar'], 0)
        self.assertGreater(heavy_pan['lead_guitar'], 0)
        self.assertGreater(heavy_gain['lead_vocal'], 1.0)
        duet_gain, duet_pan = preset_mix_values('duet')
        self.assertEqual(duet_gain['lead_vocal'], duet_gain['guest_vocal'])
        self.assertLess(duet_pan['lead_vocal'], 0)
        self.assertGreater(duet_pan['guest_vocal'], 0)
        with self.assertRaises(ValueError):
            preset_mix_values('untrusted')
        with self.assertRaises(ValueError):
            preset_mix_values('piano', ['fake_role'])

    def test_ui_applies_only_levels_and_pan_not_files_or_solo_or_offsets(self):
        panel = BandMixerPanel()
        panel.track_fields['lead_guitar'].setText('/tmp/my-personal-lead.wav')
        panel.offsets['lead_guitar'].setValue(300)
        panel.mutes['lead_guitar'].setChecked(True)
        panel.solos['lead_guitar'].setChecked(True)
        index = panel.mix_preset.findData('piano')
        panel.mix_preset.setCurrentIndex(index)
        panel.apply_mix_preset()
        self.assertEqual(panel.gains['keys'].value(), PRESETS['piano']['gains']['keys'])
        self.assertEqual(panel.gains['lead_guitar'].value(),
                         PRESETS['piano']['gains']['lead_guitar'])
        self.assertEqual(panel.track_fields['lead_guitar'].text(), '/tmp/my-personal-lead.wav')
        self.assertEqual(panel.offsets['lead_guitar'].value(), 300)
        self.assertTrue(panel.mutes['lead_guitar'].isChecked())
        self.assertTrue(panel.solos['lead_guitar'].isChecked())
        self.assertIn('Save a new project revision', panel.status.text())
        panel.close()


if __name__ == '__main__':
    unittest.main()
