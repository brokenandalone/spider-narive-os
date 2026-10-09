"""Safe Quick Settings statuses, missing tool handling and Qt smoke test."""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'the-web/shell'))
from PyQt5.QtWidgets import QApplication
import quick_settings as quick

APP=QApplication.instance() or QApplication([])


class QuickSettingsTests(unittest.TestCase):
    def test_network_bluetooth_brightness_and_battery_are_readonly(self):
        with tempfile.TemporaryDirectory() as tmp:
            power=Path(tmp)
            battery=power/'BAT0'
            battery.mkdir()
            (battery/'type').write_text('Battery\n')
            (battery/'capacity').write_text('78\n')
            (battery/'status').write_text('Charging\n')
            calls=[]
            answers={'connection':'connected\n','wifi':'enabled\n',
                     'bluetooth':'Controller local\n\tPowered: yes\n',
                     'brightness':'backlight,sysfs,63,100,63%\n',
                     'microphone':'Volume: 0.82 [MUTED]\n'}
            def fake_read(args):
                calls.append(args)
                if args[0] == 'gdbus':
                    return '(<uint32 1>,)'
                return answers[next(k for k,v in quick.STATUS_COMMANDS.items() if v==args)]
            info=quick.quick_snapshot(runner=fake_read,power_supply=power)
            self.assertEqual(info['Network'],'connected')
            self.assertEqual(info['Wi-Fi radio'],'enabled')
            self.assertEqual(info['Bluetooth'],'On')
            self.assertEqual(info['Brightness'],'63%')
            self.assertEqual(info['Microphone'],'Muted · 82%')
            self.assertEqual(info['Power'],'78% (Charging)')
            self.assertEqual(info['App color preference'], 'Dark preferred')
            self.assertEqual(len(calls),6)
            self.assertTrue(all(args in quick.STATUS_COMMANDS.values() for args in calls[:5]))

    def test_missing_tools_and_battery_are_nonfatal(self):
        with tempfile.TemporaryDirectory() as tmp:
            info=quick.quick_snapshot(runner=lambda args:None,
                power_supply=Path(tmp)/'not-present')
            self.assertIn('unavailable',info['Network'].lower())
            self.assertEqual(info['Brightness'],'Unavailable')
            self.assertIn('Unknown',info['Microphone'])
            self.assertEqual(info['Power'],'Unknown')

    def test_settings_launch_uses_exact_program_without_shell(self):
        with patch.object(quick.shutil,'which',side_effect=lambda x:'/usr/bin/systemsettings' if x=='systemsettings' else None):
            with patch.object(quick.subprocess,'Popen') as spawn:
                quick.open_kde_settings()
                self.assertEqual(spawn.call_args.args[0],['/usr/bin/systemsettings'])
                self.assertNotIn('shell',spawn.call_args.kwargs)

    def test_qt_panel_displays_snapshot_without_changing_device_state(self):
        data={'Network':'connected','Wi-Fi radio':'enabled','Bluetooth':'On',
              'Microphone':'Muted · 82%', 'Power':'No battery','Brightness':'Unavailable'}
        with patch.object(quick,'quick_snapshot',return_value=data):
            with patch.object(quick,'open_kde_settings') as launch:
                panel=quick.QuickSettingsPanel()
                self.assertTrue(panel.worker.wait(3000))
                APP.processEvents()
                self.assertIn('connected',panel.status['Network'].text())
                self.assertIn('No battery',panel.status['Power'].text())
                self.assertIn('Muted',panel.status['Microphone'].text())
                launch.assert_not_called()
                panel.close()


if __name__ == '__main__':
    unittest.main()
