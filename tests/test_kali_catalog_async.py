"""Kali Bay installed-app catalog background worker uses read-only fixed command."""
import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
UI = ROOT / "kali-bay/ui/kali_bay.py"


class KaliCatalogAsyncTests(unittest.TestCase):
    def test_worker_fixed_command_and_success_payload(self):
        script = r"""
import importlib.util
from pathlib import Path
from subprocess import CompletedProcess
from unittest.mock import patch
from PyQt5.QtWidgets import QApplication
root=Path(__import__("sys").argv[1])
spec=importlib.util.spec_from_file_location("kali_async_ui",root/"kali-bay/ui/kali_bay.py")
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
app=QApplication([])
worker=mod.KaliCatalogWorker()
received=[]
errors=[]
worker.loaded.connect(received.append)
worker.failed.connect(errors.append)
with patch.object(
    mod.subprocess,"run",
    return_value=CompletedProcess([],0,'{"applications":[]}',"")
) as run:
    worker.run()
    assert run.call_args.args[0] == [str(mod.MANAGER),"apps-json"]
    assert run.call_args.kwargs["timeout"] == 24
assert received == ['{"applications":[]}']
assert errors == []
worker2=mod.KaliCatalogWorker()
worker2.failed.connect(errors.append)
with patch.object(mod.subprocess,"run",
    return_value=CompletedProcess([],2,"","Kali not running")):
    worker2.run()
assert errors == ["Kali not running"]
"""
        result = subprocess.run(
            [sys.executable, "-c", script, str(ROOT)],
            cwd=ROOT, env=dict(os.environ, QT_QPA_PLATFORM="offscreen"),
            capture_output=True, text=True, timeout=30,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_ui_button_uses_worker_and_close_waits(self):
        source = UI.read_text()
        self.assertIn("load_apps.clicked.connect(self.start_catalog_load)", source)
        self.assertIn("worker.loaded.connect(", source)
        self.assertIn("def catalog_load_finished(self):", source)
        self.assertIn("if self.catalog_worker and self.catalog_worker.isRunning():", source)
        self.assertIn("def load_installed_desktop_apps(self, payload=None):", source)


if __name__ == "__main__":
    unittest.main()
