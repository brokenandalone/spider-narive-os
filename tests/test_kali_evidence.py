"""Read-only Kali evidence fingerprinting and no-autoshare UI tests."""
import importlib.util
import hashlib
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / "kali-bay/runtime"
spec = importlib.util.spec_from_file_location(
    "kali_evidence_tested", RUNTIME / "evidence_fingerprint.py"
)
ev = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ev)


class FingerprintTests(unittest.TestCase):
    def test_selected_file_fingerprint_only_reads(self):
        with tempfile.TemporaryDirectory() as tmp:
            file = Path(tmp) / "capture.pcap"
            original = b"\x00\x01authorized-sandbox-capture\xff"
            file.write_bytes(original)
            details = ev.fingerprint(file)
            self.assertEqual(details["sha256"], hashlib.sha256(original).hexdigest())
            self.assertEqual(details["size_bytes"], len(original))
            self.assertEqual(details["filename"], "capture.pcap")
            self.assertIn("Name: capture.pcap", ev.note_entry(details))
            self.assertIn("SHA-256:", ev.note_entry(details))
            self.assertNotIn(str(tmp), ev.note_entry(details))
            self.assertEqual(file.read_bytes(), original)
            self.assertEqual(list(Path(tmp).iterdir()), [file])

    def test_symlink_directory_and_missing_file_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sample = root / "real.bin"
            sample.write_bytes(b"good")
            alias = root / "link.bin"
            alias.symlink_to(sample)
            for selected in (alias, root, root / "not-here"):
                with self.subTest(selected=str(selected)):
                    with self.assertRaises(ev.EvidenceError):
                        ev.fingerprint(selected)

    def test_limit_and_invalid_metadata_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            file = Path(tmp) / "huge.bin"
            with file.open("wb") as handle:
                handle.truncate(ev.MAX_EVIDENCE_BYTES + 1)
            with self.assertRaisesRegex(ev.EvidenceError, "256 MiB"):
                ev.fingerprint(file)
        with self.assertRaises(ev.EvidenceError):
            ev.note_entry({"filename":"evil\ncmd", "sha256":"0"*64,
                           "size_bytes":1, "checked_utc":"2026-10-11T00:00:00+00:00"})

    def test_no_command_or_network_execution(self):
        source=(RUNTIME/"evidence_fingerprint.py").read_text()
        for fragment in ("subprocess", "os.system", "requests.", "socket.", "webbie.sock"):
            self.assertNotIn(fragment,source)


class EvidenceQtTests(unittest.TestCase):
    def test_explicit_append_requires_owner_lab_and_saved_notes(self):
        script=r"""
import importlib.util,sys,tempfile,hashlib
from pathlib import Path
from subprocess import CompletedProcess
from unittest.mock import patch
from PyQt5.QtWidgets import QApplication
root=Path(sys.argv[1])
spec=importlib.util.spec_from_file_location("kali_evidence_ui",root/"kali-bay/ui/kali_bay.py")
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
app=QApplication([])
with tempfile.TemporaryDirectory() as d:
    home=Path(d)
    base=home/".local/share/spider-os/kali-bay/projects"
    sample=home/"sample.bin"
    sample.write_bytes(b"forensic-training-evidence")
    with patch.object(Path,"home",return_value=home), \
         patch.object(mod.kali_store,"BASE",base), \
         patch.object(mod.subprocess,"run",
                      return_value=CompletedProcess([],0,"missing","")):
        win=mod.KaliBayWindow()
        lab=mod.kali_store.create_lab("Training case")
        win.refresh_labs(select_id=lab["id"])
        details=mod.kali_evidence.fingerprint(sample)
        win.evidence_lab_id=lab["id"]
        win.evidence_ready(details)
        assert not win.lab_editor.toPlainText()
        assert "SHA-256" in win.lab_status.text()
        win.append_evidence_record()
        assert details["sha256"] in win.lab_editor.toPlainText()
        assert not mod.kali_store.get_lab(lab["id"])["notes"]
        win.save_active_lab()
        assert details["sha256"] in mod.kali_store.get_lab(lab["id"])["notes"]
        assert sample.read_bytes()==b"forensic-training-evidence"
        assert not win.webbie_chat_log.toPlainText()
        win.close()
"""
        result=subprocess.run(
            [sys.executable,"-c",script,str(ROOT)],
            cwd=ROOT,env=dict(os.environ,QT_QPA_PLATFORM="offscreen"),
            capture_output=True,text=True,timeout=30,
        )
        self.assertEqual(result.returncode,0,result.stderr)


if __name__=="__main__":
    unittest.main()
