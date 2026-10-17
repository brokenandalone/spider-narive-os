"""Ubuntu Studio package preservation includes hidden audio plugins and CLI tools."""
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from contextlib import redirect_stdout

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "spider_dpkg_inventory", ROOT / "tools/ubuntu_studio_package_inventory.py")
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)


class PackagePreservationTests(unittest.TestCase):
    def test_parses_installed_status_not_removed_config_files(self):
        text = (
            "ardour\t8.4-2\tinstall ok installed\n"
            "lsp-plugins:amd64\t1.2-1\tinstall ok installed\n"
            "libreoffice-writer\t4.2-1\tinstall ok installed\n"
            "old-package\t1\tdeinstall ok config-files\n"
            "never-installed\t2\tunknown ok not-installed\n"
        )
        self.assertEqual(module.parse_installed(text), {
            "ardour": "8.4-2",
            "lsp-plugins:amd64": "1.2-1",
            "libreoffice-writer": "4.2-1",
        })

    def test_hidden_plugin_is_preserved_even_without_desktop_entry(self):
        old = module.snapshot_document({
            "ardour": "8.4", "lsp-plugins:amd64": "1.2", "guitarix": "1.0"})
        new = module.snapshot_document({"ardour": "8.5", "guitarix": "1.0"})
        result = module.compare(old, new)
        self.assertEqual(result["missing_packages"], ["lsp-plugins:amd64"])
        self.assertEqual(result["version_changes"], ["ardour"])

    def test_strict_gate_blocks_removed_package_without_modifying_packages(self):
        with tempfile.TemporaryDirectory() as folder:
            baseline = Path(folder) / "before.json"
            module.save(baseline, module.snapshot_document({
                "ardour": "1", "audioplugin": "1"}))
            self.assertEqual(baseline.stat().st_mode & 0o777, 0o600)
            with patch.object(module, "query_installed", return_value={"ardour": "2"}):
                with redirect_stdout(io.StringIO()) as output:
                    code = module.main(["--compare", str(baseline), "--strict"])
            self.assertEqual(code, 2)
            self.assertIn("REVIEW PACKAGE: audioplugin", output.getvalue())
            self.assertIn("PACKAGE PRESERVATION: BLOCKED", output.getvalue())

    def test_versions_may_change_when_packages_remain_installed(self):
        old = module.snapshot_document({"ardour": "1"})
        new = module.snapshot_document({"ardour": "2"})
        self.assertEqual(module.compare(old, new)["missing_packages"], [])

    def test_no_root_no_package_mutation_commands(self):
        source = (ROOT / "tools/ubuntu_studio_package_inventory.py").read_text()
        for token in ("sudo ", "apt purge", "apt remove",
                      "dpkg --remove", "apt autoremove", "subprocess.Popen",
                      "shell=True"):
            self.assertNotIn(token, source)
        with patch.object(module.subprocess, "run",
                          return_value=subprocess.CompletedProcess(
                              args=["dpkg-query"], returncode=0,
                              stdout="ardour\t8\tinstall ok installed\n")) as run:
            self.assertEqual(module.query_installed(), {"ardour": "8"})
        self.assertEqual(run.call_args.args[0][:2], ["dpkg-query", "-W"])
        self.assertNotIn("sudo", run.call_args.args[0])


if __name__ == "__main__":
    unittest.main()
