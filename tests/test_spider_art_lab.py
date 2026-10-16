"""Spider Art Lab project safety, real raster painting, and native-bay tests."""
import os
os.environ.setdefault("QT_QPA_PLATFORM","offscreen")

import json
from pathlib import Path
import tempfile
import unittest

from art_lab.project import (
    ArtError,new_project,add_layer,create_stroke,append_stroke,
    validate_project,save_project,open_project)

class ArtProjectTests(unittest.TestCase):
    def test_layered_project_roundtrip_preserves_original_and_is_private(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            original=new_project(128,96)
            stroke=create_stroke([(8,8),(16,16),(25,30)],
                                 tool="brush",color="#FF0033FF",width=7)
            artwork=append_stroke(original,stroke)
            artwork=add_layer(artwork,"Fine pencil")
            artwork=append_stroke(
                artwork,create_stroke([(3,4),(30,35)],
                                      tool="pencil",color="#EEEEFFFF",width=2))
            self.assertEqual(original["layers"][0]["strokes"],[])
            self.assertEqual(len(artwork["layers"]),2)
            filename=root/"Original spider painting.spiderart"
            self.assertEqual(save_project(filename,artwork),filename)
            self.assertEqual(open_project(filename),artwork)
            self.assertEqual(filename.stat().st_mode&0o777,0o600)
            original_bytes=filename.read_bytes()
            with self.assertRaises(ArtError):
                save_project(filename,original)
            self.assertEqual(filename.read_bytes(),original_bytes)
            self.assertFalse(list(root.glob("*.part")))

    def test_validation_is_strict_with_no_code_or_path_execution(self):
        for bad in (
            {"width":63},{"width":True},{"height":5000},
            {"width":4097},{"width":float("inf")},
        ):
            with self.subTest(bad=bad),self.assertRaises(ArtError):
                new_project(**bad)
        with self.assertRaises(ArtError):
            create_stroke([(0,0)],color="red")
        with self.assertRaises(ArtError):
            create_stroke([(0,float("nan"))])
        with self.assertRaises(ArtError):
            create_stroke([(0,0)],width=-1)
        with self.assertRaises(ArtError):
            create_stroke([(0,0)],tool="script")
        with self.assertRaises(ArtError):
            create_stroke([[0,0]]*8193)
        with self.assertRaises(ArtError):
            validate_project({"version":1,"width":100,"height":100,
                              "layers":[],"active":0})
        with self.assertRaises(ArtError):
            add_layer(new_project(),"x"*71)
        with self.assertRaises(ArtError):
            add_layer(new_project(),"Malformed",image_png="not-base64")

    def test_reject_symlink_and_oversized_project_without_touching_source(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            project=root/"source.spiderart"
            save_project(project,new_project(80,80))
            link=root/"linked.spiderart"
            link.symlink_to(project)
            with self.assertRaises(ArtError):
                open_project(link)
            with self.assertRaises(ArtError):
                save_project(link,new_project())
            malicious=root/"malicious.spiderart"
            malicious.write_text('{"__class__":"SomethingBad"}',encoding="utf-8")
            with self.assertRaises(ArtError):
                open_project(malicious)
            self.assertEqual(open_project(project)["width"],80)

class NativeArtLabTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            from PyQt5.QtWidgets import QApplication
        except ImportError:
            raise unittest.SkipTest("Qt is not available in this test environment")
        cls.application=QApplication.instance() or QApplication([])

    def test_actual_paint_and_eraser_render_editable_layers(self):
        from art_lab.main import render_artwork,export_artwork
        drawing=new_project(96,64)
        brush=create_stroke([(5,20),(50,20)],
                            color="#FF0000FF",tool="brush",width=7)
        drawing=append_stroke(drawing,brush)
        img=render_artwork(drawing)
        pixel=img.pixelColor(20,20)
        self.assertGreater(pixel.red(),225)
        self.assertEqual(pixel.alpha(),255)
        drawing=append_stroke(
            drawing,create_stroke([(5,20),(50,20)],
                                  tool="eraser",width=10,color="#FFFFFFFF"))
        erased=render_artwork(drawing)
        self.assertEqual(erased.pixelColor(20,20).alpha(),0)
        with tempfile.TemporaryDirectory() as folder:
            location=Path(folder)/"new-painting.png"
            self.assertEqual(export_artwork(location,drawing),location)
            self.assertEqual(location.read_bytes()[:8],b"\x89PNG\r\n\x1a\n")
            self.assertEqual(location.stat().st_mode&0o777,0o600)
            existing=location.read_bytes()
            with self.assertRaises(ArtError):
                export_artwork(location,drawing)
            self.assertEqual(location.read_bytes(),existing)

    def test_real_canvas_editor_undo_redo_and_layer_reordering(self):
        from art_lab.main import SpiderArtLab
        editor=SpiderArtLab()
        try:
            self.assertEqual(editor.document["width"],1600)
            self.assertEqual(len(editor.document["layers"]),1)
            editor.commit_paint([[10,10],[15,15]])
            self.assertEqual(len(editor.document["layers"][0]["strokes"]),1)
            editor.undo()
            self.assertFalse(editor.document["layers"][0]["strokes"])
            editor.redo()
            self.assertEqual(len(editor.document["layers"][0]["strokes"]),1)
            editor.new_layer()
            self.assertEqual(len(editor.document["layers"]),2)
            self.assertEqual(editor.document["active"],1)
            editor.lower_layer()
            self.assertEqual(editor.document["active"],0)
            editor.toggle_visible()
            self.assertFalse(editor.document["layers"][0]["visible"])
            self.assertEqual(editor.zoom.currentData(),1.0)
            editor.zoom.setCurrentIndex(1)
            self.assertEqual(editor.canvas.zoom,0.5)
        finally:
            editor.close()

    def test_existing_web_native_bay_loads_real_editor(self):
        import importlib.util
        from pathlib import Path
        root=Path(__file__).resolve().parents[1]
        spec=importlib.util.spec_from_file_location(
            "spider_artlab_bay_source",root/"the-web/shell/workspaces.py")
        module=importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.assertEqual(module.NATIVE["art-lab"],
                         ("art_lab","main.py","SpiderArtLab"))
        editor=module.create_native("art-lab",root)
        try:
            self.assertEqual(type(editor).__name__,"SpiderArtLab")
            self.assertIsNotNone(editor.canvas)
        finally:
            editor.close()

if __name__=="__main__":
    unittest.main()
