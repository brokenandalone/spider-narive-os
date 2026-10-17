"""Static cross-service vision budget checks; do not open any webcam."""
import ast
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


def default_for(relative, function_name, argument_name):
    source = ROOT / relative
    tree = ast.parse(source.read_text(encoding="utf-8"))
    fn = next(node for node in tree.body
              if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
              and node.name == function_name)
    positional = [*fn.args.posonlyargs, *fn.args.args]
    defaults = fn.args.defaults
    matched = dict(zip([arg.arg for arg in positional[-len(defaults):]], defaults))
    value = matched[argument_name]
    return ast.literal_eval(value)


class VisionLatencyBudgetTests(unittest.TestCase):
    def test_spoken_visual_request_outlives_capture_and_inference(self):
        capture = default_for("the-web/shell/webbie_camera.py", "capture_jpeg", "timeout")
        describe = default_for("the-web/shell/webbie_camera.py", "describe_frame", "timeout")
        for relative in ("webbie/agent/vision_query.py",
                         "the-web/shell/webbie_vision_bridge.py"):
            query_budget = default_for(relative, "ask_vision", "timeout")
            self.assertGreaterEqual(
                query_budget, capture + describe + 15,
                f"{relative}: Webbie must not give up before the frame can be described")

    def test_qwen_selected_for_camera_without_model_download(self):
        source = (ROOT / "the-web/shell/webbie_camera.py").read_text(encoding="utf-8")
        self.assertIn("DEFAULT_VISION_MODEL = 'qwen3-vl:2b-instruct'", source)
        self.assertIn("'-input_format', 'mjpeg'", source)
        self.assertIn("'640x480'", source)


if __name__ == "__main__":
    unittest.main()
