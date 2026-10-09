"""Read-only GTK3/GTK4/KDE appearance detection and injection resistance."""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'the-web/shell'))
import gtk_compat


class GTKCompatibilityTests(unittest.TestCase):
    def test_inventory_of_real_preferences_from_fixture_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            config=Path(tmp)
            gtk3=config/'gtk-3.0/settings.ini'
            gtk3.parent.mkdir(parents=True)
            gtk3.write_text('[Settings]\ngtk-theme-name=Breeze-Dark\ngtk-application-prefer-dark-theme=1\n')
            gtk4=config/'gtk-4.0/settings.ini'
            gtk4.parent.mkdir(parents=True)
            gtk4.write_text('[Settings]\ngtk-theme-name=Adwaita\ngtk-application-prefer-dark-theme=0\n')
            (config/'kdeglobals').write_text('[General]\nColorScheme=BreezeDark\n')
            before={str(p):p.read_bytes() for p in (gtk3,gtk4,config/'kdeglobals')}
            result=gtk_compat.appearance_snapshot(config)
            self.assertIn('Breeze-Dark',result['GTK 3'])
            self.assertIn('dark requested',result['GTK 3'])
            self.assertIn('light requested',result['GTK 4'])
            self.assertIn('not authoritative for libadwaita',result['GTK 4'])
            self.assertEqual(result['KDE colors'],'BreezeDark')
            self.assertEqual(before,{str(p):p.read_bytes() for p in (gtk3,gtk4,config/'kdeglobals')})

    def test_absent_and_malformed_files_graceful(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)
            self.assertEqual(gtk_compat.appearance_snapshot(path)['KDE colors'],'not specified')
            file=path/'kdeglobals'
            file.write_text('[General]\nColorScheme=*** malformed ***\n')
            self.assertEqual(gtk_compat.appearance_snapshot(path)['KDE colors'],'not specified')
            file.write_text('not an INI')
            self.assertEqual(gtk_compat.appearance_snapshot(path)['KDE colors'],'not specified')

    def test_no_private_symlink_following(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            secret=root/'private'
            secret.write_text('[Settings]\ngtk-theme-name=SecretTheme\n')
            g3=root/'gtk-3.0'
            g3.mkdir()
            (g3/'settings.ini').symlink_to(secret)
            self.assertNotIn('SecretTheme',gtk_compat.appearance_snapshot(root)['GTK 3'])
            self.assertEqual(secret.read_text(),'[Settings]\ngtk-theme-name=SecretTheme\n')

    def test_oversized_settings_and_markup_are_not_displayed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            file=root/'kdeglobals'
            file.write_text('[General]\nColorScheme='+('A'*20000))
            self.assertEqual(gtk_compat.appearance_snapshot(root)['KDE colors'],'not specified')
            file.write_text('[General]\nColorScheme=<a href=x>Attack</a>')
            self.assertEqual(gtk_compat.appearance_snapshot(root)['KDE colors'],'not specified')

    def test_uses_xdg_config_root_without_touching_home(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.dict(os.environ, {'XDG_CONFIG_HOME':tmp}):
                self.assertEqual(gtk_compat.config_root(),Path(tmp))
                self.assertIn('GTK 4',gtk_compat.appearance_snapshot())


if __name__=='__main__':
    unittest.main()
