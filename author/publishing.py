"""Local eBook and PDF exports. No uploading, network calls or book mutations."""
import html
import os
from pathlib import Path
import tempfile
import uuid
import zipfile


def _book(store, book_id):
    book = next((book for book in store.books() if book['id'] == book_id), None)
    if book is None:
        raise ValueError('Choose a book to export.')
    return book, store.chapters(book_id)


def export_epub(store, book_id, destination):
    """Small EPUB 3 without external dependencies; exclusive-create destination."""
    book, chapters = _book(store, book_id)
    destination = Path(destination)
    title = str(book['title'])
    identifier = str(uuid.uuid5(uuid.NAMESPACE_URL, 'spider-author:' + title + ':' + str(book_id)))
    nav = []
    spine = []
    resources = []
    with zipfile.ZipFile(destination, mode='x') as archive:
        # EPUB requires the mimetype to be the first, uncompressed member.
        archive.writestr('mimetype', 'application/epub+zip', compress_type=zipfile.ZIP_STORED)
        archive.writestr('META-INF/container.xml',
                         '<?xml version="1.0" encoding="utf-8"?>'
                         '<container xmlns="urn:oasis:names:tc:opendocument:xmlns:container" version="1.0">'
                         '<rootfiles><rootfile full-path="OEBPS/content.opf"'
                         ' media-type="application/oebps-package+xml"/></rootfiles></container>')
        archive.writestr('OEBPS/stylesheet.css',
                         'body { font-family: serif; line-height:1.55; margin:5%; }'
                         'h1 { page-break-before:always; font-size:1.5em; } p { text-indent:1.2em; }')
        for index, chapter in enumerate(chapters, 1):
            chapter_id = 'c' + str(index)
            filename = chapter_id + '.xhtml'
            content = str(chapter['content']).replace('\r\n', '\n')
            paragraphs = content.split('\n\n')
            html_paragraphs = ''.join(
                '<p>' + html.escape(p).replace('\n', '<br/>') + '</p>'
                for p in paragraphs if p.strip()
            )
            data = (
                '<?xml version="1.0" encoding="utf-8"?>'
                '<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en">'
                '<head><meta charset="utf-8"/><title>' + html.escape(chapter['title']) +
                '</title><link rel="stylesheet" type="text/css" href="stylesheet.css"/></head>'
                '<body><h1>' + html.escape(chapter['title']) + '</h1>' + html_paragraphs +
                '</body></html>'
            )
            archive.writestr('OEBPS/' + filename, data)
            resources.append('<item id="' + chapter_id + '" href="' + filename +
                             '" media-type="application/xhtml+xml"/>')
            spine.append('<itemref idref="' + chapter_id + '"/>')
            nav.append('<li><a href="' + filename + '">' +
                       html.escape(chapter['title']) + '</a></li>')
        nav_xml = ('<?xml version="1.0" encoding="utf-8"?>'
                   '<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops">'
                   '<head><title>Contents</title></head><body>'
                   '<nav epub:type="toc" id="toc"><h1>Contents</h1><ol>' +
                   ''.join(nav) + '</ol></nav></body></html>')
        archive.writestr('OEBPS/nav.xhtml', nav_xml)
        metadata = ('<metadata xmlns:dc="http://purl.org/dc/elements/1.1/">'
                    '<dc:title>' + html.escape(title) + '</dc:title>'
                    '<dc:language>en</dc:language>'
                    '<dc:identifier id="pub-id">urn:uuid:' + identifier + '</dc:identifier>'
                    '</metadata>')
        opf = ('<?xml version="1.0" encoding="utf-8"?>'
               '<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="pub-id">'
               + metadata + '<manifest>'
               '<item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>'
               '<item id="style" href="stylesheet.css" media-type="text/css"/>'
               + ''.join(resources) + '</manifest><spine>' + ''.join(spine) +
               '</spine></package>')
        archive.writestr('OEBPS/content.opf', opf)
    return destination


def export_pdf(store, book_id, destination):
    """Generate an offline selectable-text PDF with Qt and no document mutation."""
    from PyQt5.QtGui import QTextDocument
    from PyQt5.QtPrintSupport import QPrinter
    book, chapters = _book(store, book_id)
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        raise FileExistsError('That PDF already exists. Choose a new filename.')
    tmp = tempfile.NamedTemporaryFile(prefix='.author-export-', suffix='.pdf',
                                      dir=destination.parent, delete=False)
    temp_name = tmp.name
    tmp.close()
    try:
        contents = '<h1>' + html.escape(book['title']) + '</h1>'
        for chapter in chapters:
            contents += ('<div style="page-break-before:always"><h2>' +
                         html.escape(chapter['title']) + '</h2>' +
                         ''.join('<p>' + html.escape(paragraph) + '</p>'
                                 for paragraph in chapter['content'].split('\n')
                                 if paragraph.strip()) + '</div>')
        document = QTextDocument()
        document.setHtml('<html><head><meta charset="utf-8"/></head><body>' +
                         contents + '</body></html>')
        printer = QPrinter(QPrinter.HighResolution)
        printer.setOutputFormat(QPrinter.PdfFormat)
        printer.setPageSize(QPrinter.A5)
        printer.setOutputFileName(temp_name)
        document.print_(printer)
        if Path(temp_name).stat().st_size < 20:
            raise RuntimeError('PDF generation failed.')
        # Atomic link refuses an existing filename without overwriting it.
        os.link(temp_name, destination)
    finally:
        Path(temp_name).unlink(missing_ok=True)
    return destination
