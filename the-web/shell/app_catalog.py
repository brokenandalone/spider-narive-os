"""Discover installed XDG applications without executing their Exec strings."""
import configparser
import json
import re
import tempfile
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
    'productivity': 'Productivity', 'devices': 'Devices',
}

# Existing Recovery/Games tabs remain loadable for older saved sessions.
# They are not new competing first-class bays. Recovery belongs to System,
# and the Media Center can access installed games without creating another
# desktop shortcut or sacrificing any game save directory.
VISIBLE_WORKSPACES = {
    key: label for key, label in WORKSPACES.items()
    if key not in {'recovery', 'games'}
}

@dataclass(frozen=True)
class InstalledApp:
    desktop_id: str
    path: Path
    name: str
    comment: str
    icon: str
    workspace: str


# These are examples of applications already commonly shipped with Ubuntu
# Studio or used by its audio, video and graphic workflows. This mapping only
# organizes installed .desktop entries. It NEVER installs/uninstalls packages.
# Distinct software remains fully functional and searchable across bays.
APP_PURPOSES = {
    "studio": "Professional recording, MIDI, sound design, mixing or video production",
    "media": "Play and browse music, films, radio or games",
    "art-lab": "Create or edit visual artwork, photos, animation or 3D assets",
    "author": "Write and publish manuscripts or long-form documents",
    "study": "Coursework, learning and academic research",
    "forage": "Web searching, evidence gathering and browsing",
    "deep-forage": "Research, data comparison and source analysis",
    "kali-bay": "Defensive security, lab investigation and forensics",
    "communications": "Email, messaging, collaboration or file transfer",
    "productivity": "Office documents, schedules, planning and daily organization",
    "dev-bay": "Code editing, development and terminal tools",
    "devices": "Manage or inspect connected hardware, networking devices and audio routing",
    "system": "System settings, health, backup and recovery",
    "webbie": "Webbie-specific AI control and assistive tools",
}
# Exact-ish token/phrase matching avoids a word inside another word being
# mistaken for an app. Priorities explicitly separate creation from playback.
KNOWN_APPLICATIONS = (
    ("studio", ("ardour", "qtractor", "reaper", "audacity", "mixxx",
       "hydrogen", "rosegarden", "musescore", "guitarix", "rakarrack",
       "carla", "cadence", "catia", "claudia", "agordejo", "raysession",
       "ray session", "helm", "yoshimi", "zynaddsubfx", "zrythm",
       "synthv1", "samplv1", "drumkv1", "padthv1", "qsynth", "qjackctl",
       "patchage", "jack keyboard", "qpwgraph", "helvum", "easyeffects",
       "calf", "lsp plugin", "kdenlive", "shotcut", "openshot",
       "olive editor", "olive video", "obs studio", "obs-studio",
       "obsidian video", "handbrake", "k3b", "brasero")),
    ("media", ("vlc", "audacious", "mpv", "smplayer", "dragon player",
       "elisa", "rhythmbox", "strawberry", "clementine", "haruna",
       "parole", "steam", "lutris", "retroarch", "spider media center")),
    ("art-lab", ("krita", "gimp", "inkscape", "blender", "darktable",
       "digikam", "rawtherapee", "scribus", "fontforge", "mypaint",
       "pencil2d", "synfig", "freecad", "kcolorchooser", "kolourpaint")),
    ("author", ("libreoffice writer", "writer", "focuswriter", "scribus writer",
       "ghostwriter", "manuskript", "novelwriter", "sigil")),
    ("productivity", ("libreoffice calc", "libreoffice impress",
       "libreoffice draw", "libreoffice base", "libreoffice math",
       "okular", "evince", "atril", "onlyoffice", "calligra",
       "korganizer", "kontact", "calibre", "ktimetracker",
       "filelight", "xournalpp", "xournal++")),
    ("communications", ("thunderbird", "geary", "evolution", "discord",
       "element", "signal desktop", "signal-desktop", "telegram",
       "filezilla", "hexchat", "konversation", "neochat")),
    ("forage", ("firefox", "chromium", "google chrome", "brave browser",
       "vivaldi", "tor browser", "falkon", "librewolf")),
    ("study", ("anki", "klavaro", "kcalc", "calculator", "kturtle", "marble", "kalzium",
       "kstars", "stellarium")),
    ("kali-bay", ("wireshark", "nmap", "zenmap", "burpsuite",
       "burp suite", "ettercap", "maltego", "kali bay")),
    ("dev-bay", ("konsole", "kate", "kdevelop", "vscodium",
       "visual studio code", "codium", "qtcreator", "qt creator",
       "meld", "git cola", "git-cola", "gitg", "dbeaver")),
    ("devices", ("bluetooth", "kdeconnect", "kde connect", "partitionmanager",
       "partition manager", "gparted", "gsmartcontrol", "pavucontrol",
       "pulse audio volume control", "input-remapper", "usbview",
       "usb creator", "usb-creator", "kde partition manager")),
    ("system", ("timeshift", "backintime", "back in time", "spider guardian",
       "spider vault", "discover", "synaptic", "software updater",
       "system settings", "systemsettings", "grub customizer")),
)


def _has_name(identity, term):
    import re
    return bool(re.search(r"(?<![a-z0-9])" + re.escape(term) + r"(?![a-z0-9])", identity))


def workspace_for(desktop_id, name, categories):
    """Choose one PRIMARY bay, without removing an app from global search."""
    identity = (str(desktop_id) + " " + str(name)).casefold()
    values = {str(category).casefold() for category in categories}
    for bay, needles in KNOWN_APPLICATIONS:
        if any(_has_name(identity, token) for token in needles):
            return bay
    if "security" in values: return "kali-bay"
    if values & {"audiovideoediting", "audioediting", "videoediting",
                 "sequencer", "midi", "music", "recorder"}: return "studio"
    if "graphics" in values or "photography" in values: return "art-lab"
    if values & {"development", "terminalemulator", "ide"}: return "dev-bay"
    if "webbrowser" in values: return "forage"
    if values & {"education", "science"}: return "study"
    if values & {"calendar", "contactmanagement", "projectmanagement", "office"}:
        return "productivity"
    if values & {"audiovideo", "audio", "video", "player", "game"}:
        return "media"
    if "network" in values: return "communications"
    return "system"


def app_purpose(app):
    """Human-facing explanation of why an installed app is in this bay."""
    return APP_PURPOSES.get(app.workspace, "Installed application for this workspace")


def application_directories():
    home = Path(os.environ.get('XDG_DATA_HOME', str(Path.home() / '.local/share')))
    roots = [home / 'applications']
    roots += [Path(root) / 'applications' for root in os.environ.get('XDG_DATA_DIRS', '/usr/local/share:/usr/share').split(':') if root]
    roots += [home / 'flatpak/exports/share/applications', Path('/var/lib/flatpak/exports/share/applications'), Path('/var/lib/snapd/desktop/applications')]
    return list(dict.fromkeys(roots))



ASSIGNMENT_LIMIT = 40960
APP_ID_PATTERN = re.compile(r"[A-Za-z0-9_.+@-]{1,160}\Z")


def app_assignment_file(config_home=None):
    """Optional per-user placement; never alters XDG entries or packages."""
    base = Path(config_home) if config_home is not None else Path(
        os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config")))
    return base / "spider-os" / "app-placement.json"


def _guard_store(path):
    for node in (path, *path.parents):
        if node.is_symlink():
            raise OSError("Refusing symlinked app-placement settings")
        if node == node.parent:
            break
    if path.exists() and not path.is_file():
        raise OSError("App-placement settings must be a regular file")


def read_app_assignments(path=None):
    """An invalid or unreadable override file never hides installed programs."""
    path = Path(path) if path is not None else app_assignment_file()
    try:
        _guard_store(path)
        if not path.is_file() or path.stat().st_size > ASSIGNMENT_LIMIT:
            return {}
        obj = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(obj, dict) or obj.get("version") != 1:
            return {}
        rows = obj.get("assignments", {})
        if not isinstance(rows, dict):
            return {}
        return {name: bay for name, bay in rows.items()
                if isinstance(name, str) and APP_ID_PATTERN.fullmatch(name)
                and isinstance(bay, str) and bay in VISIBLE_WORKSPACES
                and bay != "default"}
    except (OSError, ValueError, TypeError, UnicodeError):
        return {}


def save_app_assignment(desktop_id, bay=None, path=None):
    """Only classification is saved. Never move/edit/remove app packages."""
    if not isinstance(desktop_id, str) or not APP_ID_PATTERN.fullmatch(desktop_id):
        raise ValueError("Unrecognized desktop application ID")
    if bay is not None and (bay not in VISIBLE_WORKSPACES or bay == "default"):
        raise ValueError("Unknown destination bay")
    path = Path(path) if path is not None else app_assignment_file()
    _guard_store(path)
    settings = read_app_assignments(path)
    if bay is None:
        settings.pop(desktop_id, None)
    else:
        settings[desktop_id] = bay
    if len(settings) > 200:
        raise ValueError("Too many manual app placements")
    output = json.dumps({"version": 1, "assignments": settings},
                        sort_keys=True, indent=2) + "\n"
    if len(output.encode("utf-8")) > ASSIGNMENT_LIMIT:
        raise ValueError("App placement settings too large")
    path.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
    _guard_store(path)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".app-placement-")
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(output)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)



def discover_apps(directories=None, desktops=None, locale=None, assignments=None):
    directories = application_directories() if directories is None else directories
    desktops = set((os.environ.get('XDG_CURRENT_DESKTOP', 'TheWeb:KDE') if desktops is None else desktops).split(':'))
    language = (locale or os.environ.get('LC_MESSAGES') or os.environ.get('LANG', '')).split('.')[0].split('@')[0]
    applications = []; seen = set()
    assignments = read_app_assignments() if assignments is None else assignments
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
                if command and not shutil.which(command[0]) and data.get('DBusActivatable', '').lower() != 'true': continue
                name = data.get(f'Name[{language}]') or data.get(f'Name[{language.split("_")[0]}]') or data.get('Name', '')
                if not name: continue
                # The desktop itself belongs in the login chooser, not its app list.
                if identity in {'the-web.desktop', 'the-web-session.desktop'}: continue
                applications.append(InstalledApp(identity, entry, name, data.get('Comment', ''), data.get('Icon', ''),
                    assignments.get(identity) if assignments.get(identity) in VISIBLE_WORKSPACES and assignments[identity] != 'default' else
                    workspace_for(identity, name, filter(None, data.get('Categories', '').split(';')))))
            except (OSError, UnicodeError, configparser.Error, KeyError, ValueError):
                continue
    return sorted(applications, key=lambda app: (app.workspace, app.name.casefold(), app.desktop_id))


def launch_command(application):
    gio = shutil.which('gio')
    if not gio: raise RuntimeError('The installed application launcher (gio) is unavailable.')
    return [gio, 'launch', str(application.path)]
