"""Bounded offline text extraction for explicitly indexed PDF and DOCX files.

No OCR, macros, network calls, attachments, remote links or file writes.
"""
from io import BytesIO
import re
import shutil
import subprocess
from xml.etree import ElementTree
from zipfile import BadZipFile, ZipFile


MAX_DOCUMENT_BYTES = 2 * 1024 * 1024
MAX_XML_BYTES = 6 * 1024 * 1024
MAX_TEXT_CHARS = 120_000


def docx_text(data):
    if not isinstance(data, bytes) or len(data) > MAX_DOCUMENT_BYTES:
        return None
    try:
        with ZipFile(BytesIO(data)) as archive:
            members = archive.infolist()
            if len(members) > 300 or sum(i.file_size for i in members) > MAX_XML_BYTES:
                return None
            document = next((m for m in members if m.filename == "word/document.xml"), None)
            if document is None or document.file_size > MAX_XML_BYTES:
                return None
            raw = archive.read(document)
            if len(raw) > MAX_XML_BYTES:
                return None
        root = ElementTree.fromstring(raw)
        ns = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
        paragraphs = []
        total = 0
        for paragraph in root.iter(ns + "p"):
            line = "".join(node.text or "" for node in paragraph.iter(ns + "t")).strip()
            if not line:
                continue
            paragraphs.append(line)
            total += len(line)
            if total >= MAX_TEXT_CHARS:
                break
        return "\n".join(paragraphs)[:MAX_TEXT_CHARS] or None
    except (BadZipFile, OSError, ValueError, ElementTree.ParseError, RuntimeError, KeyError):
        return None


def pdf_text(data):
    if not isinstance(data, bytes) or len(data) > MAX_DOCUMENT_BYTES or not data.startswith(b"%PDF-"):
        return None
    # CLI process timeout prevents one malformed PDF hanging the indexing UI.
    extractor = shutil.which("pdftotext")
    if not extractor:
        return None
    try:
        proc = subprocess.run(
            [extractor, "-layout", "-nopgbrk", "-", "-"],
            input=data, capture_output=True, timeout=10, check=False,
        )
        if proc.returncode != 0 or not proc.stdout:
            return None
        return proc.stdout.decode("utf-8", "replace")[:MAX_TEXT_CHARS].strip() or None
    except (OSError, subprocess.TimeoutExpired):
        return None


def extract_text(data, suffix):
    if suffix == ".docx":
        return docx_text(data)
    if suffix == ".pdf":
        return pdf_text(data)
    return None
