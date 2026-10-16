"""Static regression checks for the real native-bay integration.

Does not launch Qt, install files, use the microphone, or touch the desktop.
"""
import ast
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCENE_FILE = ROOT / "the-web/shell/immersive_bays.py"
SHELL_FILE = ROOT / "the-web/shell/main.py"

EXPECTED = {
    "studio", "author", "study", "kali-bay", "media",
    "webbie", "deep-forage", "art-lab",
}


class NativeImmersiveBays(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.scene = SCENE_FILE.read_text(encoding="utf-8")
        cls.shell = SHELL_FILE.read_text(encoding="utf-8")
        cls.scene_ast = ast.parse(cls.scene, filename=str(SCENE_FILE))
        cls.shell_ast = ast.parse(cls.shell, filename=str(SHELL_FILE))

    def test_python_source_compiles(self):
        compile(self.scene, str(SCENE_FILE), "exec")
        compile(self.shell, str(SHELL_FILE), "exec")

    def test_exact_eight_existing_bays(self):
        assignment = next(
            n for n in self.scene_ast.body if isinstance(n, ast.Assign)
            and any(isinstance(t, ast.Name) and t.id == "SCENES"
                    for t in n.targets)
        )
        names = {ast.literal_eval(key) for key in assignment.value.keys}
        self.assertEqual(names, EXPECTED)

    def test_native_page_is_not_replaced(self):
        self.assertIn("from immersive_bays import ImmersiveBay, SCENES", self.shell)
        self.assertIn("layout.addWidget(ImmersiveBay(name, page))", self.shell)
        self.assertIn("workspace_tabs.addTab(self.application_panel(name), 'Optional installed tools')", self.shell)
        self.assertIn("workspace_tabs.addTab(mission_desk, 'Projects & missions')", self.shell)
        self.assertIn("workspace_tabs.addTab(area, 'Native workspace')", self.shell)
        self.assertIn("workspace_tabs.addTab(surface, 'Native workspace')", self.shell)
        self.assertIn("else: native = create_native(name, SPIDER_ROOT)", self.shell)
        # Webbie has one resident panel and reuses it in the native bay.
        resident = [call for call in ast.walk(self.shell_ast)
                    if isinstance(call, ast.Call)
                    and isinstance(call.func, ast.Name)
                    and call.func.id == "WebbiePanel"]
        self.assertEqual(len(resident), 1)
        self.assertIn("workspace_tabs.addTab(operations, 'Webbie controls')", self.shell)
        self.assertIn("native.setObjectName('webbieResidentBayOverview')", self.shell)

    def test_actual_devices_productivity_and_communications_bays(self):
        self.assertIn("elif name == 'devices': native = DevicesPanel()", self.shell)
        self.assertIn("elif name == 'productivity': native = ProductivityPanel()", self.shell)
        self.assertIn("elif name == 'communications': native = CommunicationsPanel()", self.shell)
        self.assertIn("elif name == 'dev-bay': native = DevBayPanel()", self.shell)
        self.assertIn("elif name == 'art-lab': native = ArtLabPanel()", self.shell)
        self.assertIn("workspace_tabs.addTab(research_panel, 'Research mind')", self.shell)
        self.assertIn("workspace_tabs.addTab(recovery_panel, 'Recovery & backups')", self.shell)

    def test_source_preserves_active_services_and_models(self):
        forbidden = (
            "systemctl restart", "systemctl stop", "sudo ", "git push",
            "ollama pull", "rm -rf", "/dev/sda", "subprocess.run(", "os.system(",
        )
        for token in forbidden:
            self.assertNotIn(token, self.scene)

    def test_author_has_actual_clickable_landmarks(self):
        for place in (
            "Apartment 17", "Mercer & Ninth", "City Hall",
            "Platform Six", "House of Echoes",
        ):
            self.assertIn(place, self.scene)
        self.assertIn("def mousePressEvent(", self.scene)

    def test_audio_inspection_is_bounded_and_read_only(self):
        self.assertIn("def _read_wav_preview(", self.scene)
        self.assertIn("wav.setpos(", self.scene)
        self.assertIn("wav.readframes(1)", self.scene)
        self.assertNotIn("writeframes(", self.scene)

    def test_native_lifecycle_unchanged(self):
        self.assertIn("self.workspace_widgets[name] = page", self.shell)
        self.assertIn("self.tabs.setCurrentWidget(self.workspace_widgets[name])", self.shell)
        self.assertIn("self.update_webbie_context()", self.shell)


if __name__ == "__main__":
    unittest.main()
