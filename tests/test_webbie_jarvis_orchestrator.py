"""JARVIS core preserves explicit owner instructions and durable STOP."""
from pathlib import Path
import tempfile
import threading
import unittest
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"webbie/actions"))
from jarvis_orchestrator import JarvisCore
from owner_authorization_store import update_policy

class JarvisCoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.home=Path(self.tmp.name)/"home"
        self.project=self.home/"Projects"/"BCN"
        self.project.mkdir(parents=True)
        (self.project/"index.html").write_text(
            "<h1>BCN radio stream</h1>")
        self.policy=Path(self.tmp.name)/"private"/"auth.json"
        self.core=JarvisCore(policy_path=self.policy)

    def authorize(self):
        update_policy("authorize",owner_clicked=True,path=self.policy)

    def test_refuses_model_browser_or_unknown_requests(self):
        self.authorize()
        for source in ("llm","camera","webpage","socket","voice_transcript",
                       "terminal_output","background"):
            with self.subTest(source=source):
                result=self.core.run(
                    "local.evidence",source=source,folder=self.project,
                    query="radio",home=self.home)
                self.assertEqual(result.status,"denied")
        self.assertEqual(self.core.run(
            "shell.execute",source="owner_gui").status,"denied")
        self.assertEqual(self.core.status()["last_actions"],[])

    def test_owner_approved_local_evidence_and_site_audit(self):
        self.authorize()
        search=self.core.run("local.evidence",source="owner_gui",
                             folder=self.project,query="radio",
                             home=self.home)
        self.assertEqual(search.status,"observed")
        self.assertTrue(search.read_only)
        self.assertIn("index.html",search.report)
        report=self.core.run("site.audit",source="owner_gui",
                             folder=self.project,home=self.home)
        self.assertEqual(report.status,"observed")
        self.assertIn("HTML pages inspected: 1",report.report)
        self.assertFalse(self.core.status()["can_deploy_website"])
        self.assertFalse(self.core.status()["can_run_arbitrary_shell"])

    def test_stop_pause_or_revocation_discards_results(self):
        self.authorize()
        def stopping(folder,phrase,**kwargs):
            self.core.stop()
            return {"root":"BCN","scanned":1,"query":"radio",
                    "matches":[],"truncated":False}
        self.core.evidence=stopping
        result=self.core.run("local.evidence",source="owner_gui",
                             folder=self.project,query="radio",
                             home=self.home)
        self.assertEqual(result.status,"canceled")
        self.assertEqual(self.core.status()["last_actions"],[])
        update_policy("pause",path=self.policy)
        self.assertEqual(self.core.run(
            "system.health",source="owner_gui").status,"denied")

    def test_paused_mid_operation_revokes_output(self):
        self.authorize()
        def revoking(folder,phrase,**kwargs):
            update_policy("pause",path=self.policy)
            return {"root":"BCN","scanned":1,"query":"radio",
                    "matches":[],"truncated":False}
        self.core.evidence=revoking
        result=self.core.run("local.evidence",source="owner_gui",
                             folder=self.project,query="radio",
                             home=self.home)
        self.assertEqual(result.status,"canceled")

    def test_system_health_uses_only_fixed_read_only_diagnostics(self):
        self.authorize()
        calls=[]
        def diagnostic(phrase,*,authorized):
            self.assertTrue(authorized)
            calls.append(phrase)
            return "Observed"
        self.core.console=diagnostic
        report=self.core.run("system.health",source="owner_gui")
        self.assertEqual(report.status,"observed")
        self.assertEqual(len(calls),7)
        self.assertIn("No packages were installed",report.report)

    def test_concurrent_operations_do_not_overlap(self):
        self.authorize()
        started=threading.Event()
        proceed=threading.Event()
        def slow(folder,phrase,**kwargs):
            started.set()
            proceed.wait(timeout=2)
            return {"root":"BCN","scanned":1,"query":"radio",
                    "matches":[],"truncated":False}
        self.core.evidence=slow
        result=[]
        worker=threading.Thread(target=lambda:result.append(self.core.run(
            "local.evidence",source="owner_gui",folder=self.project,
            query="radio",home=self.home)))
        worker.start()
        try:
            self.assertTrue(started.wait(1))
            other=self.core.run("site.audit",source="owner_gui",
                                folder=self.project,home=self.home)
            self.assertEqual(other.status,"busy")
        finally:
            proceed.set()
            worker.join(timeout=3)
        self.assertEqual(result[0].status,"observed")

if __name__=="__main__":
    unittest.main()
