"""One click never enables privileged or destructive Spider OS operations."""
from pathlib import Path
import sys
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"webbie/actions"))
from owner_safe_access import OwnerSafeAccess,safe_app_id,MAX_ACTIONS

APPS=[
    "org.audacityteam.Audacity.desktop",
    "org.mozilla.firefox.desktop",
    "org.kde.konsole.desktop",
    "org.gnome.gparted.desktop",
    "org.kde.systemsettings.desktop",
    "kali-metasploit.desktop",
]

class OwnerWideAccessTests(unittest.TestCase):
    def setUp(self):
        self.now=[100.]
        self.access=OwnerSafeAccess(clock=lambda:self.now[0])

    def enable(self):
        return self.access.activate(APPS,owner_clicked=True)

    def test_only_explicit_owner_click_grants_all_eligible_apps(self):
        with self.assertRaises(PermissionError):
            self.access.activate(APPS)
        self.assertFalse(self.access.status()["active"])
        self.assertEqual(self.enable(),2)
        self.assertTrue(self.access.status()["active"])
        self.assertEqual(self.access.status()["eligible_apps"],2)
        self.assertEqual(self.access.status()["remaining_actions"],MAX_ACTIONS)

    def test_multiple_safe_apps_no_new_approval(self):
        self.enable()
        self.assertTrue(self.access.authorize(
            "app.open","app_id=org.audacityteam.Audacity.desktop"))
        self.assertTrue(self.access.authorize(
            "app.open","app_id=org.mozilla.firefox.desktop"))
        self.assertFalse(self.access.authorize(
            "app.open","app_id=org.kde.konsole.desktop"))
        self.assertFalse(self.access.authorize(
            "app.open","app_id=org.gnome.gparted.desktop"))
        self.assertFalse(self.access.authorize(
            "app.open","app_id=org.kde.systemsettings.desktop"))
        self.assertFalse(self.access.authorize(
            "app.open","app_id=uninstalled.desktop"))

    def test_risky_actions_stay_blocked_even_when_owner_says_all_apps(self):
        self.enable()
        bad=[
            ("pointer.click","Click in window_id=0x123"),
            ("keyboard.type","Type in window_id=0x123"),
            ("keyboard.change.confirm","Press Delete in window_id=0x123"),
            ("window.close.confirm","Close window_id=0x123"),
            ("browser.open.confirm","Open website https://a.example"),
            ("sudo","sudo anything"),("shell.execute","rm -rf"),
            ("service.send","Send email"),("service.purchase","Pay money"),
            ("system.install","Install"),("kali.execute","Attack network"),
            ("radio.broadcast","Broadcast live"),("git.push","Push code"),
        ]
        for action,preview in bad:
            with self.subTest(action=action):
                self.assertFalse(self.access.authorize(action,preview))
        self.assertEqual(self.access.status()["remaining_actions"],MAX_ACTIONS)

    def test_allowed_ui_navigation_still_requires_bound_approved_app(self):
        self.enable()
        self.assertTrue(self.access.authorize(
            "window.target","Select window_id=0x345",
            selected_app_id=APPS[0]))
        self.assertTrue(self.access.authorize(
            "window.focus","Focus window_id=0x345",
            selected_app_id=APPS[0]))
        self.assertFalse(self.access.authorize(
            "window.target","Select window_id=0x345",
            selected_app_id=APPS[2]))
        self.assertFalse(self.access.authorize(
            "window.focus","Focus other window",
            selected_app_id=APPS[0]))
        self.assertTrue(self.access.authorize(
            "keyboard.key","Press Page_Down in window_id=0x345",
            selected_app_id=APPS[0]))
        self.assertFalse(self.access.authorize(
            "keyboard.key","Press Delete in window_id=0x345",
            selected_app_id=APPS[0]))
        self.assertFalse(self.access.authorize(
            "keyboard.key","Press ctrl+s in window_id=0x345",
            selected_app_id=APPS[0]))
        self.assertFalse(self.access.authorize(
            "keyboard.key","Press Page_Down in foreground application"))

    def test_expiration_budget_and_stop_are_immediate(self):
        self.enable()
        self.now[0]+=1800
        self.assertFalse(self.access.status()["active"])
        self.assertFalse(self.access.authorize("observe.apps","List installed applications"))
        self.now[0]=2000.
        self.enable()
        for _ in range(MAX_ACTIONS):
            self.assertTrue(self.access.authorize("observe.apps","List installed applications"))
        self.assertFalse(self.access.authorize("observe.apps","List installed applications"))
        self.access.revoke()
        self.assertFalse(self.access.status()["active"])

    def test_services_status_only_no_send_upload_or_oauth(self):
        self.enable()
        for name in ("webbie","onedrive","nova"):
            self.assertTrue(self.access.authorize_service(name,"status.read"))
        for name,action in (
            ("onedrive","sync.write"),("nova","broadcast.start"),
            ("github","push"),("gmail","send"),("webbie","repair.execute")):
            self.assertFalse(self.access.authorize_service(name,action))
        self.access.revoke()
        self.assertFalse(self.access.authorize_service("nova","status.read"))

    def test_bad_app_ids_fail_closed(self):
        self.assertFalse(safe_app_id("/usr/bin/bash"))
        self.assertFalse(safe_app_id("app.desktop;rm"))
        self.assertFalse(safe_app_id("org.kde.konsole.desktop"))
        self.assertFalse(safe_app_id("org.gnome.Settings.desktop"))
        with self.assertRaises(ValueError):
            self.access.activate(["audacity.desktop",None],owner_clicked=True)
        with self.assertRaises(ValueError):
            self.access.activate(["audacity.desktop"],owner_clicked=True,seconds=1900)

if __name__=="__main__":
    unittest.main()
