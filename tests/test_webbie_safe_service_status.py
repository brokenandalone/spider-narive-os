"""Offline service access tests; never contact a real cloud or Nova stream."""
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"webbie/actions"))
from owner_safe_access import OwnerSafeAccess
from safe_service_status import (
    read_local_service_status,status_summary,LOCAL_NOVA_HEALTH
)

class FakeTransport:
    def __init__(self,content):
        self.content=content
        self.calls=[]
    def open(self,request,timeout):
        self.calls.append((request.full_url,request.get_method(),timeout))
        class Body:
            def __init__(self,c):self.c=c
            def __enter__(self):return self
            def __exit__(self,*args):pass
            def read(self,n):return self.c[:n]
        return Body(self.content)

class SafeServiceTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root=Path(temp.name)
        self.access=OwnerSafeAccess()
        self.agent=self.root/"agent.json"
        self.agent.write_text(json.dumps({"online":True,"last_heard":"SECRET"}))
        os.chmod(self.agent,0o600)
        self.drive=self.root/"onedrive.json"
        self.drive.write_text(json.dumps({"enabled":True,"token":"SECRET"}))
        os.chmod(self.drive,0o600)

    def grant(self):
        self.access.activate(["audacity.desktop"],owner_clicked=True)

    def test_no_access_without_single_click(self):
        with self.assertRaises(PermissionError):
            read_local_service_status(
                "webbie",access=self.access,agent_path=self.agent)
        with self.assertRaises(PermissionError):
            read_local_service_status(
                "nova",access=self.access,opener=FakeTransport(b'{}'))

    def test_owner_authorized_local_reports_only(self):
        self.grant()
        webbie=read_local_service_status(
            "webbie",access=self.access,agent_path=self.agent)
        drive=read_local_service_status(
            "onedrive",access=self.access,onedrive_path=self.drive)
        self.assertTrue(webbie["reported_online"])
        self.assertTrue(drive["configured"])
        self.assertFalse(drive["reported_online"])
        report=status_summary([webbie,drive])
        self.assertNotIn("SECRET",report)
        self.assertNotIn("token",report.lower())

    def test_nova_only_fixed_local_health_and_no_broadcast(self):
        self.grant()
        fake=FakeTransport(
            b'{"ok":true,"service":"Spider AI DJ","token":"SECRET"}')
        result=read_local_service_status(
            "nova",access=self.access,opener=fake)
        self.assertTrue(result["reported_online"])
        self.assertEqual(fake.calls,[(LOCAL_NOVA_HEALTH,"GET",2)])
        self.assertNotIn("SECRET",json.dumps(result))
        self.assertNotIn("broadcast.start",json.dumps(result))

    def test_nova_unavailable_fails_closed(self):
        self.grant()
        fake=FakeTransport(b'{"ok":false,"service":"Spider AI DJ"}')
        self.assertFalse(read_local_service_status(
            "nova",access=self.access,opener=fake)["reported_online"])

    def test_unprivate_files_rejected_without_leaking_contents(self):
        self.grant()
        os.chmod(self.agent,0o644)
        os.chmod(self.drive,0o644)
        self.assertFalse(read_local_service_status(
            "webbie",access=self.access,agent_path=self.agent)["reported_online"])
        self.assertFalse(read_local_service_status(
            "onedrive",access=self.access,onedrive_path=self.drive)["configured"])

if __name__=="__main__":
    unittest.main()
