"""No-network tests of deliberate school document selection for Webbie."""
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch, MagicMock

from docx import Document
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication, QListWidgetItem

from study.course_materials import (
    read_course_document, safe_remote_file, format_selected_source,
    MAX_FILE_BYTES,
)
from study.school_material_picker import SchoolMaterialPicker

app = QApplication.instance() or QApplication([])


class ReadCourseDocumentTests(unittest.TestCase):
    def test_uses_only_selected_remote_file_and_blocks_traversal(self):
        self.assertEqual(safe_remote_file("PSY-328/Week 2", "instructions.docx"),
                         "PSY-328/Week 2/instructions.docx")
        for folder, name in (
            ("../private", "paper.txt"),
            ("PSY-328", "../secrets.txt"),
            ("PSY-328", "script.exe"),
            ("", "file/other.txt"),
            ("", "A\\B.txt"),
        ):
            with self.subTest(folder=folder, name=name), self.assertRaises(ValueError):
                safe_remote_file(folder, name)

    def test_local_text_and_docx_are_readable(self):
        with tempfile.TemporaryDirectory() as root:
            text_file = Path(root) / "reading.txt"
            text_file.write_text("Course reading.", encoding="utf-8")
            self.assertEqual(read_course_document(text_file), "Course reading.")
            word_file = Path(root) / "rubric.docx"
            doc = Document()
            doc.add_paragraph("Instructor rubric.")
            doc.save(word_file)
            self.assertIn("Instructor rubric.", read_course_document(word_file))
            self.assertIn("not a citation",
                          format_selected_source("Course/rubric.docx", "Instructor rubric."))

    def test_pdf_text_extraction_requires_tool_and_handles_scans(self):
        with tempfile.TemporaryDirectory() as root:
            file = Path(root) / "instructions.pdf"
            file.write_bytes(b"%PDF-test")
            with patch("study.course_materials.shutil.which", return_value=None):
                with self.assertRaisesRegex(RuntimeError, "pdftotext"):
                    read_course_document(file)
            with patch("study.course_materials.shutil.which", return_value="/usr/bin/pdftotext"), \
                 patch("study.course_materials.subprocess.run",
                       return_value=SimpleNamespace(returncode=0, stdout="Module rubric")):
                self.assertEqual(read_course_document(file), "Module rubric")
            with patch("study.course_materials.shutil.which", return_value="/usr/bin/pdftotext"), \
                 patch("study.course_materials.subprocess.run",
                       return_value=SimpleNamespace(returncode=0, stdout="  ")):
                with self.assertRaisesRegex(ValueError, "No readable text"):
                    read_course_document(file)

    def test_rejects_links_and_oversized_files(self):
        with tempfile.TemporaryDirectory() as root:
            file = Path(root) / "too-big.txt"
            with file.open("wb") as output:
                output.truncate(MAX_FILE_BYTES + 1)
            with self.assertRaisesRegex(ValueError, "8 MB"):
                read_course_document(file)
            link = Path(root) / "link.txt"
            link.symlink_to(file)
            with self.assertRaisesRegex(ValueError, "not a link"):
                read_course_document(link)


class SchoolDocumentPickerTests(unittest.TestCase):
    def test_only_chosen_file_is_downloaded_to_a_private_temporary_folder(self):
        with tempfile.TemporaryDirectory() as root, \
             patch("study.school_material_picker.remote_ready", return_value=True), \
             patch("study.school_onedrive.remote_ready", return_value=True):
            picker = SchoolMaterialPicker(None, Path(root))
            self.assertIsNone(picker.process)
            picker.remote_folder = "SOC-112"
            item = QListWidgetItem("[File] rubric.txt")
            item.setData(Qt.UserRole, ("rubric.txt", False))
            picker.files.addItem(item)
            picker.files.setCurrentItem(item)
            with patch("study.school_material_picker.QProcess") as creator:
                process = creator.return_value
                picker.use_selected()
                args = process.setArguments.call_args.args[0]
                self.assertEqual(args[:3], ["copyto", "school_onedrive:SOC-112/rubric.txt",
                                            str(Path(picker._temporary.name) / "rubric.txt")])
                self.assertIn("--ignore-existing", args)
                self.assertTrue(Path(picker._temporary.name).exists())
                (Path(picker._temporary.name) / "rubric.txt").write_text(
                    "Compare social theories.", encoding="utf-8")
                picker.import_finished(0, 0)
            kind, excerpt = picker.selected_material
            self.assertEqual(kind, "instructions")
            self.assertIn("SOC-112/rubric.txt", excerpt)
            self.assertIn("Compare social theories.", excerpt)
            self.assertIsNone(picker._temporary)
            picker.close()

    def test_personal_style_is_explicit_and_remains_unsaved(self):
        with tempfile.TemporaryDirectory() as root, \
             patch("study.school_material_picker.remote_ready", return_value=True), \
             patch("study.school_onedrive.remote_ready", return_value=True):
            picker = SchoolMaterialPicker(None, Path(root))
            picker.remote_folder = "Writing"
            item = QListWidgetItem("[File] prior-post.txt")
            item.setData(Qt.UserRole, ("prior-post.txt", False))
            picker.files.addItem(item)
            picker.files.setCurrentItem(item)
            picker.kind.setCurrentIndex(2)
            with patch("study.school_material_picker.QProcess"):
                picker.use_selected()
                (Path(picker._temporary.name) / "prior-post.txt").write_text(
                    "A paragraph written by me.", encoding="utf-8")
                picker.import_finished(0, 0)
            self.assertEqual(picker.selected_material,
                             ("style", "A paragraph written by me."))
            picker.close()


if __name__ == "__main__":
    unittest.main()
