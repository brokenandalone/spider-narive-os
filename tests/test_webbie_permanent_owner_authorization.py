"""Owner authorization survives restart, respects durable STOP, and never leaks credentials."""
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"webbie/actions"))
from owner_authorization_store import read_policy,update_policy
from owner_safe_access import OwnerSafeAccess
from task_grants import TaskGrant

class PermanentOwnerAuthorizationTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path=Path(self.tmp.name)/"private"/"webbie-owner-authorization.json"
        self.apps=["audacity.desktop","firefox.desktop","konsole.desktop"]

    def test_owner_click_grants_indefinitely_across_restart_and_budget(self):
        with self.assertRaises(PermissionError):
            update_policy("authorize",path=self.path)
        update_policy("authorize",owner_clicked=True,path=self.path)
        record=read_policy(self.path)
        self.assertEqual(record["kali_on_demand"],True)
        self.assertTrue(record["authorized"])
        self.assertFalse(record["paused"])
        self.assertEqual(self.path.stat().st_mode&0o777,0o600)
        self.assertEqual(self.path.parent.stat().st_mode&0o777,0o700)
        now=[100.]
        first=OwnerSafeAccess(clock=lambda:now[0])
        self.assertEqual(first.restore_permanent(self.apps,path=self.path),2)
        for _ in range(290):
            self.assertTrue(first.authorize(
                "app.open","app_id=audacity.desktop"))
        self.assertIsNone(first.status()["remaining_actions"])
        self.assertIsNone(first.status()["remaining_seconds"])
        now[0]+=365*24*3600
        self.assertTrue(first.authorize(
            "app.open","app_id=firefox.desktop"))
        next_boot=OwnerSafeAccess(clock=lambda:now[0])
        self.assertEqual(next_boot.restore_permanent(self.apps,path=self.path),2)
        self.assertFalse(next_boot.authorize(
            "app.open","app_id=konsole.desktop"))

    def test_stop_pause_then_explicit_resume_without_regrant(self):
        update_policy("authorize",owner_clicked=True,path=self.path)
        update_policy("pause",path=self.path)
        paused=read_policy(self.path)
        self.assertTrue(paused["authorized"])
        self.assertTrue(paused["paused"])
        new=OwnerSafeAccess()
        self.assertEqual(new.restore_permanent(self.apps,path=self.path),0)
        with self.assertRaises(PermissionError):
            update_policy("resume",path=self.path)
        update_policy("resume",owner_clicked=True,path=self.path)
        self.assertEqual(new.restore_permanent(self.apps,path=self.path),2)
        self.assertTrue(read_policy(self.path)["kali_on_demand"])

    def test_revoke_permanent_permission(self):
        update_policy("authorize",owner_clicked=True,path=self.path)
        update_policy("revoke",owner_clicked=True,path=self.path)
        state=read_policy(self.path)
        self.assertFalse(state["authorized"])
        self.assertFalse(state["kali_on_demand"])
        self.assertTrue(state["paused"])
        with self.assertRaises(PermissionError):
            update_policy("resume",owner_clicked=True,path=self.path)
        self.assertEqual(OwnerSafeAccess().restore_permanent(
            self.apps,path=self.path),0)

    def test_unsafe_or_malformed_permission_files_fail_closed(self):
        update_policy("authorize",owner_clicked=True,path=self.path)
        os.chmod(self.path,0o644)
        self.assertFalse(read_policy(self.path)["authorized"])
        with self.assertRaises(PermissionError):
            update_policy("resume",owner_clicked=True,path=self.path)
        os.chmod(self.path,0o600)
        self.path.write_text('{"authorized":true,"paused":false}')
        self.assertFalse(read_policy(self.path)["authorized"])
        self.path.unlink()
        outside=self.path.parent/"outside"
        outside.write_text("not a real policy")
        self.path.symlink_to(outside)
        self.assertFalse(read_policy(self.path)["authorized"])
        with self.assertRaises(PermissionError):
            update_policy("authorize",owner_clicked=True,path=self.path)

    def test_task_grants_use_same_persisted_rules(self):
        update_policy("authorize",owner_clicked=True,path=self.path)
        grant=TaskGrant()
        self.assertEqual(grant.restore_permanent(self.apps,path=self.path),2)
        self.assertTrue(grant.status()["permanent"])
        self.assertTrue(grant.status()["wide"])
        self.assertTrue(grant.can_open_wide("audacity.desktop"))
        self.assertFalse(grant.can_open_wide("konsole.desktop"))
        grant.stop()
        self.assertFalse(grant.status()["active"])
        # A new login uses the durable permission (unless GUI STOP persisted).
        fresh=TaskGrant()
        self.assertEqual(fresh.restore_permanent(self.apps,path=self.path),2)

if __name__=="__main__":
    unittest.main()
