"""Regression tests for saved edit sessions, undo, grid and source protection."""
from fractions import Fraction as F
from pathlib import Path
import tempfile
import unittest

from studio.score_performer import Performance,Part,Note
from studio.score_edit_session import (
    ScoreEditor,quantized_position,encode_project,decode_project,save_project,load_project
)

def piece():
    return Performance("Test Recording",120,
                       [Part("Lead Guitar",27,0),Part("Drums",0,9)],
                       [Note(0,60,F(1,7),F(1),89),
                        Note(0,64,F(1,2),F(1),99),
                        Note(1,36,F(1),F(1,8),110)],
                       F(4),tempo_changes=[(F(2),72)]).validated()

class EditSessionTests(unittest.TestCase):
    def test_note_undo_redo_quantize_and_source_non_destructive(self):
        source=piece()
        before=list(source.notes)
        ed=ScoreEditor(source)
        self.assertEqual(quantized_position(F(1,8),4),F(1,4))
        self.assertTrue(ed.quantize(4,100,part_index=0))
        self.assertEqual(ed.score.notes[0].start,F(1,4))
        self.assertEqual(ed.score.notes[2].start,F(1))
        self.assertEqual(source.notes,before)
        self.assertTrue(ed.undo())
        self.assertEqual(ed.score.notes,before)
        self.assertTrue(ed.redo())
        self.assertEqual(ed.score.notes[0].start,F(1,4))
        self.assertTrue(ed.transpose(0,12))
        self.assertEqual([n.pitch for n in ed.score.notes],[72,76,36])
        self.assertTrue(ed.edit_note(0,pitch=73,start=F(1,3),duration=F(1,2),velocity=120))
        self.assertEqual(ed.score.notes[0].pitch,73)
        self.assertEqual(ed.score.notes[0].start,F(1,3))
        self.assertTrue(ed.delete_note(0))
        self.assertEqual(len(ed.score.notes),2)
        self.assertTrue(ed.undo())
        self.assertEqual(len(ed.score.notes),3)
        self.assertTrue(ed.set_program(0,30))
        self.assertEqual(ed.score.parts[0].program,30)

    def test_invalid_edits_are_atomic(self):
        editor=ScoreEditor(piece())
        first=list(editor.score.notes)
        for op in [lambda:editor.transpose(1,4),
                   lambda:editor.edit_note(0,pitch=129),
                   lambda:editor.edit_note(0,start=F(5)),
                   lambda:editor.quantize(0),
                   lambda:editor.quantize(4,101),
                   lambda:editor.edit_note(0,duration=F(-1))]:
            with self.subTest(op=op), self.assertRaises(ValueError):
                op()
            self.assertEqual(editor.score.notes,first)
            self.assertFalse(editor.can_undo)
        self.assertFalse(editor.undo())

    def test_versioned_project_save_load_exact_fractional_time(self):
        source=piece()
        extra={"channels":[{"gain":70,"pan":-30,"mute":False,"solo":False},
                           {"gain":99,"pan":0,"mute":False,"solo":True}],
               "groove":"Natural player", "energy":81}
        serialized=encode_project(source,extra)
        decoded,meta=decode_project(serialized)
        self.assertEqual(decoded.notes,source.notes)
        self.assertEqual(decoded.parts,source.parts)
        self.assertEqual(decoded.tempo_changes,source.tempo_changes)
        self.assertEqual(meta,extra)
        self.assertIsNone(decoded.origin)
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/"recording.spiderscore"
            save_project(path,source,extra)
            read,settings=load_project(path)
            self.assertEqual(read.notes,source.notes)
            self.assertEqual(settings,extra)
            source.origin=path
            with self.assertRaises(ValueError):
                save_project(path,source)

    def test_bad_or_malicious_project_rejected(self):
        for bad in ['{}','{"format":"other"}','x'*4_000_001]:
            with self.assertRaises(ValueError):
                decode_project(bad)
        import json
        data=json.loads(encode_project(piece()))
        data["notes"][0][2:4]=[100,0]
        with self.assertRaises(ValueError):
            decode_project(json.dumps(data))
        data=json.loads(encode_project(piece()))
        data["version"]=999
        with self.assertRaises(ValueError):
            decode_project(json.dumps(data))

if __name__=="__main__":
    unittest.main()
