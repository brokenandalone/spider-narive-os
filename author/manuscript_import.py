"""Privacy-first DOCX preview for native Spider Author.

Only main-body paragraph and table-cell text is imported. Word formatting,
images, tracked changes and comments are not imported. No network is used.
"""
from dataclasses import dataclass
import hashlib
from pathlib import Path
from xml.etree import ElementTree
from zipfile import ZipFile, BadZipFile

W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
MAX_DOCX_BYTES = 50 * 1024 * 1024
MAX_DOCUMENT_XML_BYTES = 30 * 1024 * 1024


@dataclass(frozen=True)
class ManuscriptPreview:
    title: str
    chapters: tuple
    fingerprint: str
    word_count: int


def parse_docx(path):
    """Read only; Word Heading 1 defines chapter boundaries.

    Text before the first Heading 1 becomes Front Matter. Without Heading 1,
    all text is imported intact as one chapter called Manuscript.
    """
    source = Path(path)
    if source.suffix.lower() != '.docx':
        raise ValueError('Choose a Word .docx manuscript.')
    if source.stat().st_size > MAX_DOCX_BYTES:
        raise ValueError('DOCX exceeds the 50 MB import limit.')
    fingerprint = hashlib.sha256(source.read_bytes()).hexdigest()
    try:
        with ZipFile(source) as archive:
            if '[Content_Types].xml' not in archive.namelist():
                raise ValueError('Not a valid DOCX document.')
            info = archive.getinfo('word/document.xml')
            if info.file_size > MAX_DOCUMENT_XML_BYTES:
                raise ValueError('DOCX manuscript text exceeds the import limit.')
            with archive.open(info) as stream:
                xml = stream.read(MAX_DOCUMENT_XML_BYTES + 1)
            if len(xml) > MAX_DOCUMENT_XML_BYTES:
                raise ValueError('DOCX manuscript text exceeds the import limit.')
    except (BadZipFile, KeyError) as error:
        raise ValueError('The DOCX manuscript could not be read.') from error
    try:
        document = ElementTree.fromstring(xml)
    except ElementTree.ParseError as error:
        raise ValueError('The DOCX manuscript XML is invalid.') from error
    body = document.find(W + 'body')
    if body is None:
        raise ValueError('The Word document has no manuscript body.')

    chapters = []
    current_title = None
    paragraphs = []
    for p in body.iter(W + 'p'):
        runs = []
        for element in p.iter():
            if element.tag == W + 't' and element.text:
                runs.append(element.text)
            elif element.tag == W + 'tab':
                runs.append('\t')
            elif element.tag in (W + 'br', W + 'cr'):
                runs.append('\n')
        line = ''.join(runs)
        style = p.find(W + 'pPr/' + W + 'pStyle')
        is_heading = (style is not None and
                      style.get(W + 'val', '').replace(' ', '').casefold() == 'heading1')
        if is_heading and line.strip():
            if current_title is not None:
                chapters.append((current_title, '\n'.join(paragraphs)))
            elif paragraphs and any(s.strip() for s in paragraphs):
                chapters.append(('Front Matter', '\n'.join(paragraphs)))
            current_title = line.strip()
            paragraphs = []
        else:
            paragraphs.append(line)
    if current_title is not None:
        chapters.append((current_title, '\n'.join(paragraphs)))
    elif paragraphs and any(s.strip() for s in paragraphs):
        chapters.append(('Manuscript', '\n'.join(paragraphs)))
    if not chapters or not any(content.strip() for _, content in chapters):
        raise ValueError('No manuscript body text was found in this DOCX.')
    return ManuscriptPreview(
        title=source.stem.strip() or 'Imported manuscript',
        chapters=tuple(chapters),
        fingerprint=fingerprint,
        word_count=sum(len(body.split()) for _, body in chapters),
    )
