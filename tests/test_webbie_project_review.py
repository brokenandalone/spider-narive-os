"""One owner-approved project review combines existing native Webbie tools."""
import sys
from pathlib import Path
import unittest
from unittest import mock

ROOT=Path(__file__).resolve().parents[1]
ACTIONS=str(ROOT/"webbie"/"actions")
if ACTIONS not in sys.path:
    sys.path.insert(0,ACTIONS)
import jarvis_orchestrator as core_module


class DummyPreview:
    def __init__(self):
        self.stopped=False
    def stop(self):
        self.stopped=True
    def status(self):
        return {"running":False}


class NativeProjectReviewTests(unittest.TestCase):
    def permit(self):
        return mock.patch.object(core_module,"read_policy",return_value={
            "authorized":True,"paused":False
        })

    def test_project_review_uses_both_existing_tools_once(self):
        evidence=mock.Mock(return_value={"files":["a.py"]})
        site=mock.Mock(return_value={"broken_links":[]})
        core=core_module.JarvisCore(
            evidence=evidence,site=site,preview=DummyPreview())
        with (self.permit(),
              mock.patch.object(core_module,"render_evidence",return_value="Found TODO items"),
              mock.patch.object(core_module,"render_site_report",return_value="No missing site files")):
            reply=core.run("project.review",source="owner_gui",
                           folder="/home/owner/project",query="TODO",home="/home/owner")
        self.assertEqual(reply.status,"observed")
        self.assertTrue(reply.read_only)
        self.assertIn("Found TODO items",reply.report)
        self.assertIn("No missing site files",reply.report)
        evidence.assert_called_once_with(
            "/home/owner/project","TODO",home="/home/owner",max_results=12)
        site.assert_called_once_with(
            "/home/owner/project",home="/home/owner")

    def test_untrusted_model_cannot_trigger_project_review(self):
        evidence=mock.Mock()
        core=core_module.JarvisCore(evidence=evidence,preview=DummyPreview())
        with self.permit():
            reply=core.run("project.review",source="llm",
                           folder="/home/owner/project")
        self.assertEqual(reply.status,"denied")
        evidence.assert_not_called()

    def test_stop_discards_first_stage_and_never_runs_second(self):
        site=mock.Mock()
        preview=DummyPreview()
        core=core_module.JarvisCore(site=site,preview=preview)
        def evidence(*a,**kw):
            core.stop()
            return {"secret":"should not return"}
        core.evidence=evidence
        with (self.permit(),
              mock.patch.object(core_module,"render_evidence",return_value="PRIVATE FINDINGS")):
            reply=core.run("project.review",source="owner_gui",
                           folder="/home/owner/project",query="private")
        self.assertEqual(reply.status,"canceled")
        self.assertFalse(reply.authorized)
        self.assertNotIn("PRIVATE FINDINGS",reply.report)
        site.assert_not_called()
        self.assertTrue(preview.stopped)

    def test_non_web_project_still_yields_project_files(self):
        core=core_module.JarvisCore(
            evidence=lambda *a,**kw: {"files":1},
            site=mock.Mock(side_effect=ValueError("not a site")),
            preview=DummyPreview())
        with (self.permit(),
              mock.patch.object(core_module,"render_evidence",return_value="Found work")):
            reply=core.run("project.review",source="owner_gui",
                           folder="/home/owner/project")
        self.assertEqual(reply.status,"observed")
        self.assertIn("Found work",reply.report)
        self.assertIn("Not applicable",reply.report)
        self.assertNotIn("not a site",reply.report)


if __name__=="__main__":
    unittest.main()
