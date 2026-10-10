"""Local consented RVC voice-model pointer tests, no PyTorch or audio required."""
from pathlib import Path
import json
import tempfile
import unittest

from studio import owner_voice_model as owner
from studio.voice_profile import VoiceSampleError


class OwnerModelTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.home = Path(self.tmp.name)
        self.root = self.home / 'my-voice-library'
        self.model = self.home / 'cory.pth'
        self.index = self.home / 'cory.index'
        self.model.write_bytes(b'pretend locally trained model')
        self.index.write_bytes(b'test local index')

    def test_explicit_consent_and_private_metadata_only(self):
        with self.assertRaises(VoiceSampleError):
            owner.remember_owner_model(self.model, self.index, root=self.root)
        self.assertFalse(self.root.exists())
        report = owner.remember_owner_model(self.model, self.index, consent=True, root=self.root)
        self.assertFalse(report['voice_training_verified_by_app'])
        self.assertFalse(report['audio_identity_approved'])
        saved = self.root / owner.REGISTRY
        self.assertEqual(self.root.stat().st_mode & 0o777, 0o700)
        self.assertEqual(saved.stat().st_mode & 0o777, 0o600)
        contents = saved.read_text()
        self.assertNotIn('pretend locally trained model', contents)
        self.assertEqual(json.loads(contents)['profile'], 'Justin Therapy')
        pointers = owner.load_owner_model(root=self.root)
        self.assertEqual(pointers['model'], str(self.model))
        self.assertEqual(pointers['index'], str(self.index))
        self.assertFalse(pointers['voice_training_verified_by_app'])

    def test_changed_or_missing_weights_cannot_autoload(self):
        owner.remember_owner_model(self.model, consent=True, root=self.root)
        self.assertEqual(owner.load_owner_model(root=self.root)['index'], '')
        self.model.write_bytes(self.model.read_bytes() + b' changed')
        self.assertIsNone(owner.load_owner_model(root=self.root))
        owner.remember_owner_model(self.model, self.index, consent=True, root=self.root)
        self.index.unlink()
        self.assertIsNone(owner.load_owner_model(root=self.root))

    def test_forget_does_not_delete_model_or_recordings(self):
        owner.remember_owner_model(self.model, self.index, consent=True, root=self.root)
        audio = self.root / 'sample-owner.wav'
        audio.write_bytes(b'keep the recording')
        owner.forget_owner_model(root=self.root)
        self.assertFalse((self.root / owner.REGISTRY).exists())
        self.assertTrue(self.model.exists())
        self.assertTrue(self.index.exists())
        self.assertEqual(audio.read_bytes(), b'keep the recording')
        self.assertIsNone(owner.load_owner_model(root=self.root))

    def test_model_and_registry_symlinks_are_not_trusted(self):
        linked = self.home / 'linked.pth'
        linked.symlink_to(self.model)
        with self.assertRaises(VoiceSampleError):
            owner.remember_owner_model(linked, consent=True, root=self.root)
        self.root.mkdir()
        (self.root / owner.REGISTRY).symlink_to(self.model)
        with self.assertRaises(VoiceSampleError):
            owner.remember_owner_model(self.model, consent=True, root=self.root)
        self.assertIsNone(owner.load_owner_model(root=self.root))
        with self.assertRaises(VoiceSampleError):
            owner.forget_owner_model(root=self.root)

    def test_invalid_or_corrupt_registry_is_not_loaded(self):
        self.root.mkdir()
        state = self.root / owner.REGISTRY
        for invalid in ('not json', '{}', 'null', '[1, 2]'):
            state.write_text(invalid)
            self.assertIsNone(owner.load_owner_model(root=self.root))


if __name__ == '__main__':
    unittest.main()
