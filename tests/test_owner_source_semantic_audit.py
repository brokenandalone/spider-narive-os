"""Reconciliation audit is read-only and never bundles separate applications."""
import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"tools"))
spec=importlib.util.spec_from_file_location(
    "native_semantic_audit",ROOT/"tools/owner_source_semantic_audit.py")
audit=importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


class SemanticAuditTests(unittest.TestCase):
    def test_detects_owner_only_and_candidate_only_code(self):
        owner=b"""
import os
class Owner:
    def __init__(self):
        self.live_device = True
    def hearing(self, voice):
        return voice + " owner"
    def owner_only(self):
        return 3
"""
        candidate=b"""
import sys
class Owner:
    def __init__(self):
        self.live_device = True
        self.new_video = 1
    def hearing(self, voice, urgent=False):
        return voice
    def new_feature(self):
        return self.new_video
"""
        record=audit.classify("webbie/agent/webbie.py",owner,candidate)
        self.assertIn("Owner.owner_only",record["owner_only_symbols"])
        self.assertIn("Owner.new_feature",record["candidate_only_symbols"])
        self.assertIn("Owner.hearing",record["shared_behavior_changed"])
        self.assertIn("Owner.hearing",record["shared_signature_changed"])
        self.assertEqual(record["candidate_only_constructor_fields"]["Owner"],["new_video"])
        self.assertTrue(record["needs_constructor_or_ui_wiring_review"])
        self.assertFalse(record["safe_to_auto_install"])
        self.assertTrue(record["owner_only_imports"])
        self.assertTrue(record["candidate_only_imports"])

    def test_equal_semantic_function_no_false_positive(self):
        owner=b"def answer(x):\n    return x+1\n"
        candidate=b"def answer( x ):\n    return x + 1\n"
        record=audit.classify("study/study.py",owner,candidate)
        self.assertFalse(record["shared_behavior_changed"])
        self.assertFalse(record["shared_signature_changed"])

    def test_shared_change_never_called_auto_installable(self):
        owner=b"def answer(x):\n    return 1\n"
        candidate=b"def answer(x):\n    return 2\n"
        record=audit.classify("webbie/brain/brain.py",owner,candidate)
        self.assertEqual(record["shared_behavior_changed"],["answer"])
        self.assertEqual(record["action"],
                         "OWNER_BASIS_RETAINED; NO_AUTOMATIC_REPLACEMENT")
        self.assertFalse(record["safe_to_auto_install"])

    def test_shell_scripts_need_explicit_review(self):
        record=audit.classify("kali-bay/bin/kali-bay",b"#!/bin/bash\ntrue\n",
                              b"#!/bin/bash\nfalse\n")
        self.assertTrue(record["shell_semantic_diff_requires_review"])
        self.assertFalse(record["safe_to_auto_install"])

    def test_summary_requires_all_31_to_be_reviewed(self):
        rows=[audit.classify("study/study.py",b"def f(): return 3\n",
                             b"def g(): return 4\n") for _ in range(31)]
        summary=audit.summarize(rows)
        self.assertEqual(summary["files"],31)
        self.assertEqual(summary["candidate_only_symbol_count"],31)
        self.assertEqual(summary["release_status"],
                         "NOT_READY_CODE_RECONCILIATION_REQUIRED")

    def test_reading_is_static_and_does_not_execute_script(self):
        with tempfile.TemporaryDirectory() as tmp:
            marker=Path(tmp)/"should_not_exist"
            code=(f"from pathlib import Path\nPath({str(marker)!r}).touch()\n"
                  "def hello(): return True\n").encode()
            info=audit.index_code(code,"webbie/agent/webbie.py")
            self.assertIn("hello",info["symbols"])
            self.assertFalse(marker.exists())

    def test_webbie_voice_overwrites_are_explicitly_not_safe(self):
        owner=b"def listen_forever(on_text, should_continue, on_interrupt=None):\n    pass\n"
        proposed=b"def listen_forever(on_text, should_continue, on_interrupt=None, verifier=None):\n    pass\n"
        record=audit.classify("webbie/voice/whisper_listener.py",owner,proposed)
        self.assertIn("listen_forever",record["shared_signature_changed"])
        self.assertFalse(record["safe_to_auto_install"])


if __name__=="__main__":
    unittest.main()
