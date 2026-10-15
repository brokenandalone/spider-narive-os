import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('app_catalog', ROOT/'the-web/shell/app_catalog.py')
import sys
catalog=importlib.util.module_from_spec(spec);sys.modules[spec.name]=catalog;spec.loader.exec_module(catalog)

class CatalogTests(unittest.TestCase):
    def write(self, folder, name, extra=''):
        path=Path(folder)/name;path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text('[Desktop Entry]\nType=Application\nName=Ardour\nExec=ardour %U\nCategories=AudioVideo;AudioVideoEditing;\n'+extra)
        return path

    def test_overrides_visibility_localization_and_placement(self):
        with tempfile.TemporaryDirectory() as folder:
            user=Path(folder)/'user';system=Path(folder)/'system'
            self.write(system,'hidden.desktop');self.write(user,'hidden.desktop','Hidden=true\n')
            self.write(system,'nodisplay.desktop','NoDisplay=true\n')
            self.write(system,'other.desktop','OnlyShowIn=GNOME;\n')
            self.write(system,'excluded.desktop','NotShowIn=KDE;\n')
            valid=self.write(system,'ardour.desktop','Name[en_GB]=Recording\nOnlyShowIn=KDE;\n')
            self.write(system,'missing.desktop','TryExec=absent\n')
            with patch.object(catalog.shutil,'which',side_effect=lambda x: None if x=='absent' else '/bin/'+x):
                apps=catalog.discover_apps([user,system],desktops='TheWeb:KDE',locale='en_GB.UTF-8')
            self.assertEqual(len(apps),1);self.assertEqual(apps[0].path,valid)
            self.assertEqual(apps[0].name,'Recording');self.assertEqual(apps[0].workspace,'studio')
            with patch.object(catalog.shutil,'which',return_value='/usr/bin/gio'):
                self.assertEqual(catalog.launch_command(apps[0]),['/usr/bin/gio','launch',str(valid)])

    def test_category_mapping(self):
        for name,categories,expected in [('Kdenlive',['Video'],'studio'),('VLC',['AudioVideo','Player'],'media'),('Krita',['Graphics'],'art-lab'),('Writer',['Office'],'author'),('Firefox',['Network','WebBrowser'],'forage'),('Thunderbird',['Network'],'communications'),('Konsole',['TerminalEmulator'],'dev-bay'),('Calculator',['Science'],'study'),('Timeshift',['System'],'recovery'),('Steam',['Game'],'games')]:
            self.assertEqual(catalog.workspace_for(name,name,categories),expected)

if __name__=='__main__':unittest.main()
