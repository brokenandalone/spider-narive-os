#!/usr/bin/env python3
"""Reconcile two known Spider OS launcher variants without overwriting custom code.

This is intentionally narrow: unrelated modifications are reported and left alone.
The desktop installer backs up original files before invoking this helper.
"""
from pathlib import Path
import argparse
import ast
import hashlib
import os
import tempfile


AUTHOR_BLOCK = """    if document is None:
        script = ROOT / 'author/main.py'
        if not script.is_file():
            raise AppUnavailable('The native Author module is missing.')
        try:
            __import__('PyQt5.QtWidgets')
        except ImportError:
            raise AppUnavailable('Author requires python3-pyqt5.') from None
        return ['python3', str(script)]
"""

STUDIO_OLD_NOTE = """        content.addSpacing(20)
        note = QLabel(
            'Spider Media Center is the Media module.\\n'
            'Webbie remains the resident AI service shared across Spider OS.'
        )
        note.setStyleSheet('color: #82788d;')
        content.addWidget(note)
        content.addStretch()

"""

STUDIO_OLD_ACTIONS = """    def launch(self, command):
        try:
            subprocess.Popen(command)
            self.status.setText('Launched: ' + ' '.join(command))
        except Exception as exc:
            self.status.setText(str(exc))

    def launch_music(self):
        for command in ('ardour8', 'ardour', 'carla'):
            path = shutil.which(command)
            if path:
                self.launch([path])
                return
        self.status.setText('No supported DAW is installed. Install Ardour or Carla to use Music Studio.')

"""

# Exact Git blob IDs for older Study versions known to be on the upgrade path.
# These fingerprints prevent overwriting unfamiliar owner-local modifications.
# Git SHA-1 here identifies known content; it is not used for authentication.
STUDY_KNOWN_BLOBS = {
    'Study workspace': {
        '456f0279b397f7776b8ba9c6d970d493a9a8ccaf',  # original main
        '422029cbc30b462d87ff52eaa6c608b63f9ce499',  # School PR #8
    },
    'Study course store': {
        'c7fa2cef87f66f187e6253a7059f7a5d335703f0',  # original main
    },
}


def git_blob_sha(content):
    data = content.encode('utf-8')
    header = b'blob ' + str(len(data)).encode('ascii') + b'\\0'
    return hashlib.sha1(header + data).hexdigest()


def one_replace(text, old, new):
    if text.count(old) != 1:
        raise ValueError('Unrecognized upstream source; preserving installed code.')
    return text.replace(old, new, 1)


def legacy_studio(upstream):
    """Reconstruct exactly the locally customized older Studio seen on the PC."""
    result = upstream
    result = one_replace(result, '    QFrame, QGridLayout, QScrollArea, QTabWidget,\n', '    QFrame,\n')
    result = one_replace(result,
        "sys.path.insert(0, str(Path(__file__).resolve().parent))\n"
        "if __package__:\n"
        "    from .tools import TOOLS, resolve_tool\n"
        "    from .ai_panel import StudioAIPanel\n"
        "else:\n"
        "    from tools import TOOLS, resolve_tool\n"
        "    from ai_panel import StudioAIPanel\n", '')
    style = (
        "            QWidget { background: #0c0a10; color: #eeeaf3; }\n"
        "            QTabBar::tab { background:#21172d; color:#e9d5ff; padding:8px; }\n"
        "            QTabBar::tab:selected { background:#4c1d95; }\n"
        "            QTabWidget::pane, QScrollArea { border:1px solid #4c1d95; }\n"
        "            QPushButton:disabled { background:#17121d; color:#93869e; border-color:#352543; }\n"
    )
    result = one_replace(result, style, '')
    result = one_replace(result,
        "logo.setFont(QFont('Sans Serif', 18, QFont.Bold))",
        "logo.setFont(QFont('Sans Serif', 22, QFont.Bold))")
    result = one_replace(result,
        'content.setContentsMargins(24, 24, 24, 24)',
        'content.setContentsMargins(50, 48, 50, 48)')
    start, end = '        self.tool_tabs = QTabWidget()\n', '        footer = QLabel('
    if result.count(start) != 1 or result.count(end) != 1:
        raise ValueError('Upstream Studio tab layout changed.')
    a = result.index(start); b = result.index(end, a)
    result = result[:a] + STUDIO_OLD_NOTE + result[b:]
    a = result.index('    def launch(self, command):\n')
    b = result.index('    def media_command(self):\n', a)
    result = result[:a] + STUDIO_OLD_ACTIONS + result[b:]
    ast.parse(result)
    return result


def enhanced_studio(upstream):
    result = one_replace(upstream,
        "logo.setFont(QFont('Sans Serif', 18, QFont.Bold))",
        "logo.setFont(QFont('Sans Serif', 22, QFont.Bold))")
    result = one_replace(result,
        'content.setContentsMargins(24, 24, 24, 24)',
        'content.setContentsMargins(50, 48, 50, 48)')
    result = one_replace(result,
        '        self.refresh_tools()\n\n        footer = QLabel(',
        '        self.refresh_tools()\n\n' + STUDIO_OLD_NOTE.replace('content.addSpacing(20)', 'content.addSpacing(8)').replace('        content.addStretch()\n', '') + '        footer = QLabel(')
    result = one_replace(result,
        "self.status.setText('Application opened.')",
        "self.status.setText('Launched: ' + ' '.join(command))")
    ast.parse(result)
    return result


def atomic_replace(path, content):
    data = content.encode('utf-8')
    with tempfile.NamedTemporaryFile(dir=path.parent, prefix='.spider-reconcile-', delete=False) as stream:
        candidate = Path(stream.name)
        stream.write(data)
    try:
        os.chmod(candidate, path.stat().st_mode & 0o777)
        candidate.replace(path)
    finally:
        candidate.unlink(missing_ok=True)


def reconcile(source, installed, kind):
    if not installed.is_file() or not source.is_file():
        print(f'{kind}: source or installed entry absent, skipping')
        return 'missing'
    upstream, current = source.read_text(), installed.read_text()
    if current == upstream:
        print(f'{kind}: already current')
        return 'current'
    if kind == 'Author launcher':
        if upstream.count(AUTHOR_BLOCK) != 1:
            raise ValueError('Upstream Author launcher changed.')
        expected_old = upstream.replace(AUTHOR_BLOCK, '', 1)
        if current != expected_old:
            print('Author launcher: unfamiliar local changes, preserving; manual review required')
            return 'conflict'
        replacement = upstream
    elif kind == 'Studio':
        if 'self.tool_tabs = QTabWidget()' in current:
            print('Studio: tools tabs already present; preserving local version')
            return 'current'
        if current != legacy_studio(upstream):
            print('Studio: unfamiliar local changes, preserving; manual review required')
            return 'conflict'
        replacement = enhanced_studio(upstream)
    elif kind in STUDY_KNOWN_BLOBS:
        if git_blob_sha(current) not in STUDY_KNOWN_BLOBS[kind]:
            print(f'{kind}: unknown local edits, preserving; manual review required')
            return 'conflict'
        replacement = upstream
    else:
        raise ValueError(f'Unsupported reconciliation type: {kind}')
    ast.parse(replacement)
    atomic_replace(installed, replacement)
    print(f'{kind}: reconciled exactly known local variant')
    return 'reconciled'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('source_root', type=Path)
    parser.add_argument('installed_root', type=Path)
    arguments = parser.parse_args()
    source, root = arguments.source_root, arguments.installed_root
    results = [
        reconcile(source / 'system/apps.py', root / 'system/apps.py', 'Author launcher'),
        reconcile(source / 'studio/main.py', root / 'studio/main.py', 'Studio'),
    ]
    # The dashboard calls store.all_assignments(): upgrade the dependency first.
    store_status = reconcile(source / 'study/store.py', root / 'study/store.py', 'Study course store')
    results.append(store_status)
    if store_status in ('current', 'reconciled'):
        results.append(reconcile(source / 'study/study.py', root / 'study/study.py', 'Study workspace'))
    else:
        print('Study workspace: skipped until the course store is reviewed')
    return 0 if 'conflict' not in results and store_status != 'missing' else 2


if __name__ == '__main__':
    raise SystemExit(main())
