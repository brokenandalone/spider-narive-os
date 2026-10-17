#!/usr/bin/env python3
"""Small import compatibility patches; preserve the owner's native app source."""
from pathlib import Path
import re
import sys

root = Path(sys.argv[1])
for relative, modules in [('author/main.py', ['store']), ('studio/main.py', ['tools']), ('study/study.py', ['store', 'apa'])]:
    path = root / relative
    if not path.exists():
        print(f'{relative}: not installed; no changes')
        continue
    source = path.read_text(); updated = source
    for module in modules:
        if re.search(r'from \.' + module + r' import', source):
            continue
        # Match single/multiline from-imports without changing their contents.
        pattern = re.compile(r'(?m)^(?P<indent> *)from ' + module + r' import (?P<body>\([^)]*\)|[^\n]+)')
        def substitute(match):
            indent = match['indent']; statement = match.group(0)[len(indent):]
            nested = '\n'.join(indent + '    ' + line for line in statement.splitlines())
            relative_statement = nested.replace('from ' + module + ' import', 'from .' + module + ' import', 1)
            return indent + 'if __package__:\n' + relative_statement + '\n' + indent + 'else:\n' + nested
        updated = pattern.sub(substitute, updated)
    if relative == 'study/study.py':
        old = "        self.save_notes(\n            quiet=True\n        )\n\n        self.store.close()\n\n        event.accept()"
        new = "        try:\n            self.save_notes(quiet=True)\n        except Exception as error:\n            self.status.setText('Notes could not be saved: ' + str(error))\n            event.ignore()\n            return\n        self.store.close()\n        event.accept()"
        updated = updated.replace(old, new)
    if updated != source:
        compile(updated, str(path), 'exec')
        path.write_text(updated)
        print(f'{relative}: import compatibility updated')
    else:
        print(f'{relative}: already compatible')
