"""Study saved-reading UI receives the course context already passed by StudyWindow."""
import ast
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]

class StudyReadingIntegrationTests(unittest.TestCase):
    def test_homework_dialog_accepts_existing_study_context(self):
        source=(ROOT/"study"/"homework_ui.py").read_text()
        tree=ast.parse(source)
        dialog=next(node for node in tree.body
                    if isinstance(node,ast.ClassDef) and node.name=="HomeworkDialog")
        init=next(node for node in dialog.body
                  if isinstance(node,ast.FunctionDef) and node.name=="__init__")
        names=[x.arg for x in init.args.kwonlyargs]
        self.assertIn("store",names)
        self.assertIn("course_id",names)
        self.assertIn("import_course_reading",
                      {n.name for n in dialog.body if isinstance(n,ast.FunctionDef)})
        self.assertIn('("Select a saved course reading", self.import_course_reading)',source)
    def test_study_does_not_require_course_when_opening_assistant(self):
        study=(ROOT/"study"/"study.py").read_text()
        self.assertIn("if self.current_course_id else None",study)
        self.assertIn("store=self.store if course else None",study)
        self.assertIn("course_id=self.current_course_id if course else None",study)
    def test_reading_is_owner_picked_before_insert(self):
        source=(ROOT/"study"/"homework_ui.py").read_text()
        self.assertIn("pick=True",source)
        self.assertIn("QDialog.Accepted and picker.selected_excerpt",source)
        self.assertIn('self.add_selected_material("materials", picker.selected_excerpt)',source)
        self.assertNotIn("subprocess.Popen",source)

if __name__=="__main__":
    unittest.main()
