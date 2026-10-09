"""The Web local content navigation must never move or expose private files."""
import importlib.util
from pathlib import Path
import tempfile
import unittest


SOURCE = Path(__file__).resolve().parents[1] / 'the-web/shell/workspace_files.py'
spec = importlib.util.spec_from_file_location('workspace_files', SOURCE)
mapping = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mapping)


class WorkspaceFileTests(unittest.TestCase):
    def test_real_author_studio_and_school_paths(self):
        home = Path('/home/test-user')
        self.assertEqual(mapping.workspace_folders('author', home)[0][1],
                         home / 'Documents/Spider OS/Author')
        self.assertEqual(mapping.workspace_folders('studio', home)[0][1],
                         home / 'Documents/Spider Studio')
        self.assertEqual(mapping.workspace_folders('study', home)[0][1],
                         home / 'Documents/Spider OS/Study')
        self.assertEqual(mapping.workspace_folders('dev-bay', home)[0][1],
                         home / 'spider-narive-os')

    def test_all_desktop_workspaces_have_local_content_navigation(self):
        from importlib.util import spec_from_file_location, module_from_spec
        source = SOURCE.parent / 'app_catalog.py'
        spec = spec_from_file_location('app_catalog_workspace', source)
        app = module_from_spec(spec)
        import sys
        sys.modules[spec.name] = app
        spec.loader.exec_module(app)
        for workspace in app.WORKSPACES:
            self.assertTrue(mapping.workspace_folders(workspace), workspace)

    def test_open_requires_existing_folder_never_creates_or_moves(self):
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d) / 'not-present'
            with self.assertRaises(FileNotFoundError):
                mapping.file_open_command(folder, which=lambda _: '/usr/bin/xdg-open')
            self.assertFalse(folder.exists())
            folder.mkdir()
            self.assertEqual(mapping.file_open_command(folder, which=lambda _: '/usr/bin/xdg-open'),
                             ['/usr/bin/xdg-open', str(folder)])
            self.assertTrue(folder.is_dir())

    def test_missing_launcher_does_not_guess_file_manager(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaisesRegex(RuntimeError, 'xdg-open'):
                mapping.file_open_command(folder, which=lambda _: None)


if __name__ == '__main__':
    unittest.main()
