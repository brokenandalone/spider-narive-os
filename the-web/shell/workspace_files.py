"""Known local content folders for Spider OS workspaces.

No private documents, database files or model weights are copied or created here.
Only existing folders are exposed; optional paths are deliberately not invented.
"""
from pathlib import Path


def workspace_folders(workspace, home=None):
    home = Path.home() if home is None else Path(home)
    documents = home / 'Documents'
    spider = documents / 'Spider OS'
    research = spider / 'Research'
    entries = {
        'default': [('Spider OS documents', spider)],
        'author': [
            ('Author manuscript library', spider / 'Author'),
            ('Original Word manuscripts', spider / 'Author' / 'Originals'),
        ],
        'studio': [
            ('Spider Studio projects', documents / 'Spider Studio'),
            ('Music files', home / 'Music'),
        ],
        'study': [
            ('School coursework and APA files', spider / 'Study'),
        ],
        'forage': [('Research files', research)],
        'deep-forage': [('Deep Forage projects', research / 'Deep Forage'), ('Research files', research)],
        'webbie': [('Webbie project files', spider / 'Webbie')],
        'art-lab': [('Artwork and images', home / 'Pictures'), ('Art Lab projects', spider / 'Art Lab')],
        'media': [('Music library', home / 'Music'), ('Video library', home / 'Videos'), ('Photo library', home / 'Pictures')],
        'kali-bay': [('Security project files', spider / 'Kali Bay')],
        'dev-bay': [('Spider OS source', home / 'spider-narive-os'), ('Development projects', spider / 'Dev Bay')],
        'communications': [('Communications documents', spider / 'Communications')],
        'recovery': [('Spider OS upgrade backups', spider / 'Upgrade Backups'), ('Local recovery files', home / 'Spider-OS-Backups')],
        'system': [('Spider OS documents', spider)],
        'games': [('Games and saves', spider / 'Games')],
    }
    return [(label, path) for label, path in entries.get(workspace, [])]


def file_open_command(path, which=None):
    """Open an existing directory with the desktop's default file manager."""
    from shutil import which as system_which
    path = Path(path).expanduser()
    if not path.is_dir():
        raise FileNotFoundError(f'Workspace folder not found: {path}')
    executable = (which or system_which)('xdg-open')
    if not executable:
        raise RuntimeError('xdg-open is not installed on this desktop.')
    return [executable, str(path)]
