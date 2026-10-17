"""Existing short task permission and new broad session remain separate."""
import importlib.util
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
PATH=ROOT/"webbie/actions/task_grants.py"
spec=importlib.util.spec_from_file_location("testwide_grants",PATH)
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

APPS=["audacity.desktop","firefox.desktop","konsole.desktop"]

class OneClickGrantTests(unittest.TestCase):
    def test_activate_wide_and_change_app_without_regrant(self):
        now=[100.]
        grant=module.TaskGrant(clock=lambda:now[0])
        self.assertFalse(grant.status()["active"])
        with self.assertRaises(PermissionError):
            grant.activate_wide(APPS)
        self.assertEqual(grant.activate_wide(APPS,owner_clicked=True),2)
        self.assertTrue(grant.status()["wide"])
        self.assertTrue(grant.select_wide_app(APPS[0]))
        self.assertTrue(grant.authorize("app.open","app_id=audacity.desktop"))
        self.assertTrue(grant.select_wide_app(APPS[1]))
        self.assertTrue(grant.authorize("app.open","app_id=firefox.desktop"))
        self.assertFalse(grant.select_wide_app(APPS[2]))
        self.assertFalse(grant.authorize("app.open","app_id=konsole.desktop"))
        self.assertFalse(grant.authorize(
            "keyboard.type","Type in window_id=0x1"))
        self.assertFalse(grant.authorize(
            "browser.open.confirm","https://example.org"))
        self.assertTrue(grant.authorize(
            "window.target","Select window_id=0x1") is False)
        self.assertTrue(grant.select_wide_app(APPS[0]))
        self.assertTrue(grant.authorize("window.target","Select window_id=0x1"))
        self.assertTrue(grant.authorize("keyboard.key","Press Page_Down in window_id=0x1"))
        self.assertFalse(grant.authorize("keyboard.key","Press Delete in window_id=0x1"))
        grant.stop()
        self.assertFalse(grant.status()["active"])
        self.assertTrue(grant.status()["stopped"])
        self.assertFalse(grant.authorize("app.open","app_id=audacity.desktop"))

    def test_normal_task_still_allows_existing_sensitive_confirm_after_owner_click(self):
        called=[]
        grant=module.TaskGrant(approve_sensitive=lambda action,preview:
                               called.append((action,preview)) or True)
        grant.activate_wide(APPS,owner_clicked=True)
        self.assertFalse(grant.authorize(
            "window.close.confirm","Close window_id=0x1"))
        self.assertEqual(called,[])
        grant.stop()
        grant.activate("Close currently saved window","audacity.desktop")
        self.assertFalse(grant.status()["wide"])
        self.assertTrue(grant.authorize(
            "window.close.confirm","Close window_id=0x1"))
        self.assertEqual(len(called),1)

    def test_expiration_blocks_and_task_mode_not_implicitly_resumed(self):
        now=[10.]
        grant=module.TaskGrant(clock=lambda:now[0])
        grant.activate("Earlier task","audacity.desktop")
        grant.activate_wide(APPS,owner_clicked=True)
        now[0]+=1801
        self.assertFalse(grant.status()["active"])
        self.assertFalse(grant.authorize("keyboard.key","Press Page_Down in window_id=0x1"))

if __name__=="__main__":
    unittest.main()
