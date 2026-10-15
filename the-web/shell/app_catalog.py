"""Discover installed XDG applications without executing their Exec strings."""
import configparser
from dataclasses import dataclass
import os
from pathlib import Path
import shlex
import shutil

WORKSPACES = {
    'default': 'The Web', 'webbie': 'Webbie', 'forage': 'Forage',
    'deep-forage': 'Deep Forage', 'studio': 'Studio', 'author': 'Author',
    'art-lab': 'Art Lab', 'dev-bay': 'Dev Bay', 'study': 'School',
    'media': 'Media', 'communications': 'Communications', 'kali-bay': 'Kali Bay',
    'system': 'System', 'recovery': 'Recovery', 'games': 'Games',
}

@dataclass(frozen=True)
class InstalledApp:
    desktop_id: str
    path: Path
    name: str
    comment: str
    icon: str
    workspace: str


def workspace_for(desktop_id, name, categories):
    identity = (desktop_id + ' ' + name).lower()
    categories = set(categories)
    if any(word in identity for word in ('timeshift', 'backintime', 'spider-guardian', 'spider-vault')):
        return 'recovery'
    if any(word in identity for word in ('ardour', 'qtractor', 'audacity', 'lmms', 'carla', 'hydrogen', 'mixxx', 'qjackctl', 'easyeffects', 'helvum', 'kdenlive', 'shotcut', 'openshot', 'handbrake', 'obs-studio')):
        return 'studio'
    if 'Security' in categories or any(word in identity for word in ('kali-bay', 'wireshark', 'nmap', 'burpsuite')): return 'kali-bay'
    if 'Graphics' in categories: return 'art-lab'
    if categories & {'Development', 'TerminalEmulator'}: return 'dev-bay'
    if categories & {'Education', 'Science'}: return 'study'
    if 'Office' in categories: return 'author'
    if categories & {'AudioVideoEditing', 'AudioEditing', 'Midi', 'Sequencer'}: return 'studio'
    if categories & {'AudioVideo', 'Audio', 'Video', 'Player'}: return 'media'
    if 'WebBrowser' in categories: return 'forage'
    if 'Network' in categories: return 'communications'
    if 'Game' in categories: return 'games'
    return 'system'


def application_directories():
    home = Path(os.environ.get('XDG_DATA_HOME', str(Path.home() / '.local/share')))
    roots = [home / 'applications']
    roots += [Path(root) / 'applications' for root in os.environ.get('XDG_DATA_DIRS', '/usr/local/share:/usr/share').split(':') if root]
    roots += [home / 'flatpak/exports/share/applications', Path('/var/lib/flatpak/exports/share/applications'), Path('/var/lib/snapd/desktop/applications')]
    return list(dict.fromkeys(roots))


def discover_apps(directories=None, desktops=None, locale=None):
    directories = application_directories() if directories is None else directories
    desktops = set((os.environ.get('XDG_CURRENT_DESKTOP', 'TheWeb:KDE') if desktops is None else desktops).split(':'))
    language = (locale or os.environ.get('LC_MESSAGES') or os.environ.get('LANG', '')).split('.')[0].split('@')[0]
    applications = []; seen = set()
    for root in directories:
        root = Path(root)
        if not root.is_dir(): continue
        for entry in sorted(root.rglob('*.desktop')):
            identity = str(entry.relative_to(root)).replace('/', '-')
            if identity in seen: continue
            seen.add(identity)  # Hidden user overrides must mask system entries.
            parser = configparser.ConfigParser(interpolation=None, strict=False)
            parser.optionxform = str
            try:
                parser.read(entry, encoding='utf-8')
                data = parser['Desktop Entry']
                if data.get('Type') != 'Application': continue
                if any(data.get(key, '').lower() == 'true' for key in ('Hidden', 'NoDisplay')): continue
                only = set(filter(None, data.get('OnlyShowIn', '').split(';')))
                excluded = set(filter(None, data.get('NotShowIn', '').split(';')))
                if (only and not desktops & only) or desktops & excluded: continue
                executable = data.get('TryExec')
                if executable and not shutil.which(executable): continue
                command = shlex.split(data.get('Exec', ''))
                if not command and data.get('DBusActivatable', '').lower() != 'true': continue
                if command and not shutil.which(command[0]): continue
                name = data.get(f'Name[{language}]') or data.get(f'Name[{language.split("_")[0]}]') or data.get('Name', '')
                if not name: continue
                # The desktop itself belongs in the login chooser, not its app list.
                if identity in {'the-web.desktop', 'the-web-session.desktop'}: continue
                applications.append(InstalledApp(identity, entry, name, data.get('Comment', ''), data.get('Icon', ''),
                    workspace_for(identity, name, filter(None, data.get('Categories', '').split(';')))))
            except (OSError, UnicodeError, configparser.Error, KeyError, ValueError):
                continue
    return sorted(applications, key=lambda app: (app.workspace, app.name.casefold(), app.desktop_id))


def launch_command(application):
    gio = shutil.which('gio')
    if not gio: raise RuntimeError('The installed application launcher (gio) is unavailable.')
    return [gio, 'launch', str(application.path)]
