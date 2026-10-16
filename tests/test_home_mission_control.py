"""Home Mission Control must prioritize real cross-bay work without execution."""
import ast
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
SOURCE=(ROOT/"the-web/shell/home_dashboard.py").read_text(encoding="utf-8")
tree=ast.parse(SOURCE)
function=next(node for node in tree.body
              if isinstance(node,ast.FunctionDef) and node.name=="focus_queue")
module=ast.Module(body=[function],type_ignores=[])
namespace={"PURPOSES":{"studio":"music","study":"learning","system":"health"},
           "BLUEPRINTS":{"studio":("Studio",()),"study":("Study",()),"system":("System",())}}
exec(compile(ast.fix_missing_locations(module),str(ROOT),"exec"),namespace)
focus_queue=namespace["focus_queue"]

class FocusQueueTests(unittest.TestCase):
    def test_blocked_then_active_then_next(self):
        rows=[{"bay":"study","status":"next","title":"Finish paper"},
              {"bay":"studio","status":"active","title":"Record album"},
              {"bay":"system","status":"blocked","title":"Backup disk"},
              {"bay":"studio","status":"done","title":"Old export"}]
        actual=focus_queue(rows)
        self.assertEqual([x["status"] for x in actual],["blocked","active","next"])
        self.assertEqual([x["bay"] for x in actual],["system","studio","study"])
    def test_limit_and_untrusted_rows(self):
        rows=[{},None,{"bay":"unknown","status":"blocked","title":"Ignore"},
              {"bay":"studio","status":"active","title":"x"*200}]
        actual=focus_queue(rows,limit=1)
        self.assertEqual(len(actual),1)
        self.assertEqual(len(actual[0]["title"]),140)
        with self.assertRaises(ValueError):focus_queue(rows,limit=0)
    def test_focus_does_not_open_project_files(self):
        self.assertNotIn("subprocess",SOURCE)
        self.assertIn("self.workspace_opener(bay)",SOURCE)

if __name__=="__main__":
    unittest.main()
