"""Regression: reject unsafe archive members before restore writes anything."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

from studio.multitrack import SessionError
from studio.session_archive import ARCHIVE_NAME, _index_archive
from studio.session_project import MAX_MANIFEST_BYTES
from studio.session_presets import MAX_PRESET_BYTES


def make_archive(path, members):
    index = {"schema": 1, "application": "Spider Audio Studio",
             "project_title": "Test Song", "members": {}}
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_STORED) as archive:
        for name, content in members.items():
            archive.writestr(name, content)
            index["members"][name] = {
                "size": len(content),
                "sha256": hashlib.sha256(content).hexdigest(),
            }
        archive.writestr(ARCHIVE_NAME, json.dumps(index))


class ArchiveMemberLimitTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "song.zip"
        self.wav = {"01-lead_guitar.wav": b"RIFF"}

    def inspect(self):
        with zipfile.ZipFile(self.path) as archive:
            return _index_archive(archive)

    def test_accepts_normal_bounded_archive_index(self):
        make_archive(self.path, {"session.json": b"{}", **self.wav})
        index, total = self.inspect()
        self.assertEqual(total, 6)
        self.assertIn("01-lead_guitar.wav", index["members"])

    def test_rejects_oversized_manifest_before_extraction(self):
        make_archive(self.path, {
            "session.json": b"x" * (MAX_MANIFEST_BYTES + 1), **self.wav})
        with self.assertRaisesRegex(SessionError, "manifest is oversized"):
            self.inspect()

    def test_rejects_oversized_mix_preset_before_extraction(self):
        make_archive(self.path, {
            "session.json": b"{}", **self.wav,
            "mix-presets/preset-" + "a" * 32 + ".json":
                b"x" * (MAX_PRESET_BYTES + 1)})
        with self.assertRaisesRegex(SessionError, "mix preset is oversized"):
            self.inspect()

    def test_rejects_more_than_24_wavs(self):
        members = {"session.json": b"{}"}
        for i in range(1, 26):
            members[f"{i:02d}-lead_guitar.wav"] = b"RIFF"
        make_archive(self.path, members)
        with self.assertRaisesRegex(SessionError, "unsupported number"):
            self.inspect()

    def test_rejects_manifest_without_a_wav(self):
        make_archive(self.path, {"session.json": b"{}"})
        with self.assertRaisesRegex(SessionError, "unsupported number"):
            self.inspect()


if __name__ == "__main__":
    unittest.main()
