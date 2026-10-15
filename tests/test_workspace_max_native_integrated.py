"""Regression tests for MAX features embedded in actual native Spider OS bays."""
import ast
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SHELL = (ROOT / "the-web/shell/main.py").read_text(encoding="utf-8")
BRIDGE = (ROOT / "the-web/shell/workspace_max_native.py").read_text(encoding="utf-8")


class NativeMaxIntegrationTests(unittest.TestCase):
    def test_source_compiles(self):
        compile(SHELL, "main.py", "exec")
        compile(BRIDGE, "workspace_max_native.py", "exec")

    def test_native_original_app_kept(self):
        self.assertIn("create_native(name, SPIDER_ROOT)", SHELL)
        self.assertIn("native = WebbiePanel(SPIDER_ROOT)", SHELL)
        self.assertIn("native = MediaPanel(self.launch_media)", SHELL)
        self.assertIn("workspace_tabs.addTab(area, 'Original workspace')", SHELL)
        self.assertIn("workspace_tabs.addTab(surface, 'Original workspace')", SHELL)
        self.assertIn("workspace_tabs.addTab(advanced, 'Advanced tools & tasks')", SHELL)

    def test_operations_embedded_not_launched(self):
        self.assertIn("NativeWorkspaceTools(name, workspace_tabs)", SHELL)
        self.assertIn("catalog.run(self.workspace, self.action, self.folder, self.query)", BRIDGE)
        self.assertNotIn("subprocess.", BRIDGE)
        self.assertNotIn("QProcess", BRIDGE)
        self.assertNotIn("spider-os-workspace-max", BRIDGE)
        self.assertIn("QThread", BRIDGE)

    def test_verified_v4_sources_only(self):
        self.assertIn("V4_SHA256", BRIDGE)
        self.assertIn("V4_BLOB_SHA256", BRIDGE)
        self.assertIn('"__init__.py": "dc7d5bdc', BRIDGE)
        self.assertIn('candidate.is_symlink()', BRIDGE)
        self.assertIn('sha_file(candidate) != V4_SHA256', BRIDGE)

    def test_nova_and_backups_embedded(self):
        self.assertIn('"bcn-nova": "BCN / Nova"', BRIDGE)
        self.assertIn('"backups": "Backups"', BRIDGE)
        self.assertIn("NativeWorkspaceTools('bcn-nova', workspace_tabs)", SHELL)
        self.assertIn("NativeWorkspaceTools('backups', workspace_tabs)", SHELL)

    def test_no_native_service_writes(self):
        for dangerous in (
            'systemctl restart', 'systemctl stop', 'sudo ', 'ollama pull',
            'setfacl', 'git push', 'os.system(', 'subprocess.run(',
        ):
            self.assertNotIn(dangerous, BRIDGE)

    def test_workspace_worker_blocks_close(self):
        self.assertIn("Finish workspace analysis before closing this bay.", SHELL)
        self.assertIn("worker and worker.isRunning()", SHELL)

    def test_eight_immersive_bays_preserved(self):
        self.assertIn("layout.addWidget(ImmersiveBay(name, page))", SHELL)
        self.assertIn("bay_row.addWidget(self.application_panel(name))", SHELL)


if __name__ == "__main__":
    unittest.main()
