"""Kali Bay local evidence chain integrity, private permissions and explicit Qt events."""
import importlib.util
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / "kali-bay/runtime"
sys.path.insert(0, str(RUNTIME))
import workspace_store as store
import evidence_ledger as ledger
import evidence_fingerprint as evidence
import lab_reports as reports


class EvidenceLedgerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        home = Path(self.temp.name)
        home_patch = patch.object(Path, "home", return_value=home)
        base_patch = patch.object(
            store, "BASE", home / ".local/share/spider-os/kali-bay/projects",
        )
        home_patch.start()
        base_patch.start()
        self.addCleanup(home_patch.stop)
        self.addCleanup(base_patch.stop)
        self.lab = store.create_lab("Permitted forensic lab")
        self.meta = {
            "filename": "capture.pcap",
            "size_bytes": 18,
            "sha256": hashlib.sha256(b"permitted evidence").hexdigest(),
            "checked_utc": "2026-10-11T19:00:00+00:00",
        }

    def test_explicit_chain_with_private_files_and_valid_reports(self):
        self.assertEqual(ledger.read_ledger(self.lab["id"])["events"], [])
        self.assertEqual(ledger.verify_ledger(self.lab["id"])["count"], 0)
        first = ledger.append_event(
            self.lab["id"], "registered", self.meta, "Owner approved capture.",
        )
        self.assertEqual(first["number"], 1)
        self.assertEqual(first["previous_hash"], "0" * 64)
        second = ledger.append_event(
            self.lab["id"], "reviewed", self.meta, "Metadata checked offline.",
        )
        self.assertEqual(second["number"], 2)
        self.assertEqual(second["previous_hash"], first["entry_hash"])
        actual = ledger.verify_ledger(self.lab["id"])
        self.assertTrue(actual["verified"])
        self.assertEqual(actual["count"], 2)
        self.assertEqual(actual["head"], second["entry_hash"])
        self.assertIn("local saved records", ledger.ledger_summary(self.lab["id"]))
        ledger_file = ledger._ledger_path(self.lab["id"])
        lock_file = ledger._lock_path(self.lab["id"])
        self.assertEqual(stat.S_IMODE(ledger_file.stat().st_mode), 0o600)
        self.assertEqual(stat.S_IMODE(lock_file.stat().st_mode), 0o600)
        exported = reports.export_saved_report(self.lab["id"])
        self.assertIn("Metadata checked offline", exported.read_text())
        self.assertIn(second["entry_hash"], exported.read_text())
        self.assertIn("not real-world custody", exported.read_text().lower() if
                      "not real-world custody" in exported.read_text().lower() else
                      ledger.ledger_summary(self.lab["id"]).lower())

    def test_tampering_refuses_new_events_and_report_exports(self):
        ledger.append_event(
            self.lab["id"], "registered", self.meta, "Authorized work.",
        )
        ledger_file = ledger._ledger_path(self.lab["id"])
        document = json.loads(ledger_file.read_text())
        document["events"][0]["note"] = "Fabricated investigation claim."
        ledger_file.write_text(json.dumps(document))
        with self.assertRaisesRegex(store.StorageError, "hash mismatch"):
            ledger.read_ledger(self.lab["id"])
        with self.assertRaises(store.StorageError):
            ledger.append_event(self.lab["id"], "reviewed", self.meta, "Review.")
        with self.assertRaises(store.StorageError):
            reports.export_saved_report(self.lab["id"])
        self.assertFalse((store.BASE / "reports").exists())

    def test_foreign_lab_rejected_and_input_limits(self):
        for identifier in ("../../etc/passwd", "", "a" * 33):
            with self.subTest(identifier=identifier):
                with self.assertRaises(store.StorageError):
                    ledger.read_ledger(identifier)
        with self.assertRaises(store.StorageError):
            ledger.append_event("a" * 32, "registered", self.meta, "no lab")
        with self.assertRaises(store.StorageError):
            ledger.append_event(self.lab["id"], "other", self.meta, "no")
        with self.assertRaises(store.StorageError):
            ledger.append_event(self.lab["id"], "registered", self.meta, "")
        with self.assertRaises(store.StorageError):
            ledger.append_event(self.lab["id"], "registered", self.meta, "x" * 501)
        bad = dict(self.meta, filename="script\ninline")
        with self.assertRaises(store.StorageError):
            ledger.append_event(self.lab["id"], "registered", bad, "Review")
        self.assertFalse(ledger._ledger_path(self.lab["id"]).exists())

    def test_symlinked_lock_and_ledger_refused(self):
        with tempfile.TemporaryDirectory() as elsewhere:
            reference = Path(elsewhere) / "file"
            reference.write_text("outside")
            ledger._lock_path(self.lab["id"]).symlink_to(reference)
            with self.assertRaisesRegex(store.StorageError, "Linked ledger lock"):
                ledger.append_event(
                    self.lab["id"], "registered", self.meta, "Allowed",
                )
            self.assertEqual(reference.read_text(), "outside")
            ledger._lock_path(self.lab["id"]).unlink()
            ledger._ledger_path(self.lab["id"]).symlink_to(reference)
            with self.assertRaises(store.StorageError):
                ledger.read_ledger(self.lab["id"])
            self.assertEqual(reference.read_text(), "outside")

    def test_only_local_and_no_process_execution(self):
        source = (RUNTIME / "evidence_ledger.py").read_text()
        for forbidden in ("subprocess", "socket.", "requests.", "os.system",
                          "distrobox enter", "podman exec"):
            self.assertNotIn(forbidden, source)


class EvidenceLedgerUiTests(unittest.TestCase):
    def test_offscreen_user_confirmed_event_and_integrity_panel(self):
        script = r"""
import importlib.util, sys, tempfile, hashlib
from pathlib import Path
from unittest.mock import patch
from subprocess import CompletedProcess
from PyQt5.QtWidgets import QApplication, QMessageBox
root=Path(sys.argv[1])
spec=importlib.util.spec_from_file_location("ledger_ui",root/"kali-bay/ui/kali_bay.py")
ui=importlib.util.module_from_spec(spec)
spec.loader.exec_module(ui)
app=QApplication([])
with tempfile.TemporaryDirectory() as d:
    base=Path(d)/".local/share/spider-os/kali-bay/projects"
    with patch.object(Path, "home", return_value=Path(d)), \
         patch.object(ui.kali_store, "BASE", base), \
         patch.object(ui.subprocess, "run",
                      return_value=CompletedProcess([],0,"missing","")):
        win=ui.KaliBayWindow()
        assert win.security_tabs.count()==6
        assert win.security_tabs.tabText(5)=="EVIDENCE LEDGER"
        assert win.findChild(ui.QWidget,"kaliEvidenceLedgerPage")
        lab=ui.kali_store.create_lab("Sandbox custody")
        win.refresh_labs(select_id=lab["id"])
        win.evidence_lab_id=lab["id"]
        win.evidence_result={
            "filename":"sample.bin","size_bytes":3,
            "sha256":hashlib.sha256(b"abc").hexdigest(),
            "checked_utc":"2026-10-11T20:00:00+00:00",
        }
        win.ledger_note.setText("Owner approved this stored sample.")
        with patch.object(QMessageBox, "question", return_value=QMessageBox.Yes):
            win.record_evidence_event()
        assert len(ui.kali_ledger.read_ledger(lab["id"])["events"])==1
        assert win.ledger_list.count()==1
        assert "local SHA-256 link" in win.ledger_status.text()
        win.ledger_kind.setCurrentText("reviewed")
        win.ledger_note.setText("Reviewed metadata without execution.")
        with patch.object(QMessageBox, "question", return_value=QMessageBox.Yes):
            win.record_evidence_event()
        assert len(ui.kali_ledger.read_ledger(lab["id"])["events"])==2
        win.refresh_evidence_ledger()
        assert "local chain VALID" in win.ledger_status.text()
        assert not win.webbie_chat_log.toPlainText()
        win.close()
"""
        result = subprocess.run(
            [sys.executable, "-c", script, str(ROOT)],
            cwd=ROOT, env=dict(os.environ, QT_QPA_PLATFORM="offscreen"),
            capture_output=True, text=True, timeout=35,
        )
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
