"""Author release manifest completeness and private-data exclusion tests."""
import ast
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
AUTHOR_MODULES = {
    'author/main.py', 'author/store.py', 'author/web_features.py',
    'author/speech.py', 'author/publishing.py',
    'author/review_engine.py', 'author/review_cache.py',
    'author/review_history.py', 'author/continuity_engine.py',
    'author/narration_bookmarks.py', 'author/voice_reader.py',
    'author/commands.py', 'author/commands_client.py',
    'author/control_socket.py', 'author/manuscript_import.py',
    'author/project_map.py',
    'author/story_atlas.py', 'author/atlas_widget.py',
    'author/master_canon.py', 'author/master_canon_widget.py',
}
WEBBIE_BRIDGE = 'webbie/agent/author_voice_bridge.py'


def targeted_manifest():
    source = (ROOT / 'the-web/package/install-author-webbie.sh').read_text()
    match = re.search(r'(?m)^managed=\(\s*\n(.*?)^\)', source, re.S | re.M)
    if match is None:
        raise AssertionError('Targeted installer manifest is missing.')
    return [
        line.strip() for line in match.group(1).splitlines()
        if line.strip() and not line.strip().startswith('#')
    ]


def combined_manifest():
    source = ast.parse((ROOT / 'system/release_batch.py').read_text())
    for stmt in source.body:
        if isinstance(stmt, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == 'APP_FILES'
            for target in stmt.targets
        ):
            return list(ast.literal_eval(stmt.value))
    raise AssertionError('Combined release APP_FILES is missing.')


class AuthorInstallManifestTests(unittest.TestCase):
    def test_targeted_author_upgrade_includes_all_dependencies(self):
        listed = targeted_manifest()
        self.assertEqual(len(listed), len(set(listed)), 'No duplicate targets')
        self.assertTrue(AUTHOR_MODULES.issubset(listed))
        self.assertIn(WEBBIE_BRIDGE, listed)

    def test_combined_spider_os_release_includes_all_author_dependencies(self):
        listed = combined_manifest()
        self.assertEqual(len(listed), len(set(listed)), 'No duplicate targets')
        self.assertTrue(AUTHOR_MODULES.issubset(listed))
        self.assertIn(WEBBIE_BRIDGE, listed)

    def test_no_manuscripts_databases_or_private_documents_are_copied(self):
        for manifest in (targeted_manifest(), combined_manifest()):
            for path in manifest:
                self.assertNotIn('Documents/', path)
                self.assertNotIn('/home/', path)
                self.assertNotIn('library.sqlite', path)
                self.assertFalse(path.lower().endswith(('.docx','.epub','.pdf','.db')))


if __name__ == '__main__':
    unittest.main()
