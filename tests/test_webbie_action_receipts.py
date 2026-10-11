"""Webbie desktop receipts are truthful, privacy-safe and short-lived."""
import importlib.util
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location(
    "webbie_action_receipts_test", ROOT/"webbie/actions/action_receipts.py")
m=importlib.util.module_from_spec(spec)
sys.modules[spec.name]=m
spec.loader.exec_module(m)

class ReceiptTests(unittest.TestCase):
    def test_requested_never_claims_success(self):
        current=[100.]
        ledger=m.ActionReceipts(clock=lambda:current[0])
        receipt=ledger.record("website","requested")
        self.assertEqual(receipt.outcome,"requested")
        self.assertIn("completion not verified",ledger.summary())
        self.assertNotIn("loaded",ledger.summary())
        self.assertNotIn("success",ledger.summary())

    def test_expiring_and_clear(self):
        clock=[100.]
        book=m.ActionReceipts(clock=lambda:clock[0])
        book.record("navigation","observed")
        self.assertIsNotNone(book.snapshot())
        clock[0]=191
        self.assertIsNone(book.snapshot())
        book.record("stop","canceled")
        book.clear()
        self.assertEqual(book.summary(),"No recent desktop action receipt.")

    def test_only_fixed_redacted_fields(self):
        book=m.ActionReceipts()
        for value in ("https://example.com","password","/tmp/secret",""):
            with self.subTest(value=value),self.assertRaises(ValueError):
                book.record(value,"requested")
            with self.subTest(outcome=value),self.assertRaises(ValueError):
                book.record("website",value)
        self.assertEqual(book.summary(),"No recent desktop action receipt.")

    def test_all_statuses_explicit(self):
        book=m.ActionReceipts()
        for action in sorted(m.ACTIONS):
            for result in sorted(m.OUTCOMES):
                report=m.status_text(book.record(action,result))
                self.assertIn(action.title(),report)
                self.assertNotIn("https://",report)

    def test_context_does_not_include_operation_content(self):
        book=m.ActionReceipts()
        book.record("application","denied")
        self.assertIn("denied",book.advisory_summary())
        self.assertNotIn("application.exe",book.advisory_summary())

if __name__=="__main__":
    unittest.main()
