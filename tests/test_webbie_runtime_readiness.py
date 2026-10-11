"""Webbie system readiness is derived only from small owner-local status."""
import json
from datetime import datetime
from pathlib import Path
import os
import stat
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"webbie/agent"))
sys.path.insert(0,str(ROOT/"webbie/brain"))
import runtime_readiness as m
from jarvis_context import publish_context
from privacy_controls import set_private_session, DEFAULT_PATH as PRIVACY_PATH
from unittest.mock import patch

class ReadinessTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root=Path(temp.name)
        self.agent=self.root/"webbie.json"
        self.context=self.root/"context.json"
        self.proactive=self.root/"checks.json"
        self.privacy=self.root/"privacy.json"

    def collect(self):
        with patch("privacy_controls.DEFAULT_PATH",self.privacy),patch(
                "runtime_readiness.private_session_active",
                create=True,return_value=False):
            return m.inspect_readiness(
                agent_path=self.agent,context_path=self.context,
                proactive_path=self.proactive)

    def test_no_status_never_claims_operational(self):
        report=self.collect()
        statuses={x.key:x.status for x in report}
        self.assertEqual(statuses["agent"],"unknown")
        self.assertEqual(statuses["microphone"],"unknown")
        self.assertEqual(statuses["speaker_identity"],"unavailable")
        self.assertIn("not proof",m.render_report(report).lower())

    def test_real_recent_agent_heartbeat_is_only_reported(self):
        self.agent.write_text(json.dumps({
            "online":True,"voice_listener":True,
            "updated":datetime.now().isoformat(),
        }))
        os.chmod(self.agent,0o600)
        report={x.key:x for x in self.collect()}
        self.assertEqual(report["agent"].status,"reported")
        self.assertEqual(report["microphone"].status,"reported")
        self.assertIn("unverified",report["microphone"].detail)

    def test_explicit_microphone_error_is_warning(self):
        self.agent.write_text(json.dumps({"voice_listener":False}))
        os.chmod(self.agent,0o600)
        report={x.key:x for x in self.collect()}
        self.assertEqual(report["microphone"].status,"warning")

    def test_gui_context_is_read_without_sensitive_pixels(self):
        publish_context(path=self.context,workspace="studio",
                        selected_title="Guitar mix",clock=None)
        values={x.key:x for x in self.collect()}
        self.assertEqual(values["workspace"].status,"reported")
        self.assertNotIn("Guitar mix",m.render_report(tuple(values.values())))

    def test_world_readable_files_ignored(self):
        self.agent.write_text(json.dumps({
            "online":True,"voice_listener":True,
            "updated":datetime.now().isoformat(),
        }))
        os.chmod(self.agent,0o644)
        report={x.key:x for x in self.collect()}
        self.assertEqual(report["agent"].status,"unknown")

    def test_proactive_category_count_only(self):
        self.proactive.write_text(json.dumps({
            "checks":{"microphone":{"detail":"private device name"},
                      "disk":{"detail":"private path"}}}))
        os.chmod(self.proactive,0o600)
        report=m.render_report(self.collect())
        self.assertIn("2 check categories",report)
        self.assertNotIn("private device name",report)
        self.assertNotIn("private path",report)

    def test_symlink_state_rejected(self):
        other=self.root/"outside"
        other.write_text(json.dumps({"online":True,
                                     "updated":datetime.now().isoformat()}))
        self.agent.symlink_to(other)
        values={x.key:x for x in self.collect()}
        self.assertEqual(values["agent"].status,"unknown")

if __name__=="__main__":
    unittest.main()
