"""Check Webbie's Kali doctor uses only audited existing read-only manager command."""
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock
import subprocess

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"webbie"/"agent"))
import kali_assistant


class KaliDoctorTests(unittest.TestCase):
    def test_literal_kali_doctor_routes_only_exact_phrases(self):
        for phrase in ("check kali diagnostics", "show kali bay diagnostics",
                       "Hey Webbie, run Kali Doctor"):
            self.assertEqual(kali_assistant.parse_request(phrase),("doctor",None))
        for phrase in ("run kali doctor && sudo apt upgrade",
                       "diagnose kali and scan the subnet",
                       "doctor rm -rf /"):
            self.assertNotEqual(kali_assistant.parse_request(phrase),("doctor",None))

    def test_exact_diagnostic_never_starts_container_or_installs(self):
        with tempfile.TemporaryDirectory() as directory:
            manager=Path(directory)/"kali-bay"
            manager.write_text("#!/bin/sh\nexit 0\n")
            manager.chmod(0o700)
            response=subprocess.CompletedProcess(
                args=[],returncode=0,stdout="KALI BAY DIAGNOSTICS (READ ONLY)\nContainer: running\n",stderr="")
            with mock.patch.object(kali_assistant.subprocess,"run",return_value=response) as runner:
                reply=kali_assistant.handle_kali_request(
                    "check kali diagnostics",manager=manager)
            runner.assert_called_once()
            args,kwargs=runner.call_args
            self.assertEqual(args[0],[str(manager),"doctor"])
            self.assertEqual(kwargs["timeout"],22)
            self.assertFalse(kwargs["check"])
            self.assertIn("Container: running",reply)
            self.assertIn("did not start a container",reply)

    def test_diagnostic_timeout_reports_failure_without_fake_success(self):
        with tempfile.TemporaryDirectory() as directory:
            manager=Path(directory)/"kali-bay"
            manager.write_text("#!/bin/sh\nexit 0\n")
            manager.chmod(0o700)
            with mock.patch.object(kali_assistant.subprocess,"run",
                                   side_effect=subprocess.TimeoutExpired(["doctor"],22)):
                reply=kali_assistant.handle_kali_request(
                    "check kali diagnostics",manager=manager)
            self.assertIn("unavailable",reply)


if __name__=="__main__":
    unittest.main()
