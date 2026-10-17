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
# Validated against the owner's real 174-entry Ubuntu Studio 26.04
# application-menu inventory, 2026-10-15. These are *placements only*.
# They never delete, move or replace the underlying installed programs.
# Specific XDG desktop IDs fix cases where broad AudioVideo/Graphics
# categories don't distinguish synths from players or Linux audio
# hardware mixers from music production.
UBUNTU_STUDIO_DESKTOP_IDS = {
    "studio": (
        "spider-studio.desktop",
        "studio.desktop",
        "aeolus.desktop",
        "zita-at1.desktop",
        "devede_ng.py.desktop",
        "dgedit.desktop",
        "din.desktop",
        "qlcplus-fixtureeditor.desktop",
        "fluidsynth-dssi.desktop",
        "fmit.desktop",
        "freewheeling.desktop",
        "hexter.desktop",
        "jack_mixer.desktop",
        "meterbridge.desktop",
        "patchance.desktop",
        "phasex.desktop",
        "qlcplus.desktop",
        "com.cuperino.qprompt.desktop",
        "org.kde.krecorder.desktop",
        "setbfree.desktop",
        "sooperlooper.desktop",
        "xjadeo.desktop",
        "zita-mu1.desktop",
        "zita-rev1.desktop",
        "org.jacktrip.JackTrip.desktop",
        "ubuntustudio-audio-config.desktop",
    ),
    "media": (
        "idjc.desktop",
        "org.kde.kid3.desktop",
        "org.kde.kid3-qt.desktop",
        "freeshow_freeshow.desktop",
        "openlp.desktop",
        "spider-media-player.desktop",
    ),
    "devices": (
        "envy24control.desktop",
        "org.ffado.FfadoMixer.desktop",
        "hdajackretask.desktop",
        "hdspconf.desktop",
        "hdspmixer.desktop",
        "mudita24.desktop",
        "qasconfig.desktop",
        "qashctl.desktop",
        "qasmixer.desktop",
        "org.kde.qrca.desktop",
        "kde_wacom_tabletfinder.desktop",
    ),
    "art-lab": (
        "org.kde.spectacle.desktop",
        "org.gnome.ColorProfileViewer.desktop",
    ),
    "author": (
        "author.desktop",
    ),
    "forage": (
        "forage.desktop",
    ),
    "deep-forage": (
        "deep-forage.desktop",
    ),
    "study": (
        "study.desktop",
    ),
    "webbie": (
        "webbie.desktop",
        "webbie-face-sleep-tonight.desktop",
        "webbie-face-wake.desktop",
        "webbie-onedrive-connect.desktop",
        "spider-webbie-intelligence.desktop",
    ),
    "kali-bay": (
        "kali-bay.desktop",
    ),
    "system": (
        "spider-os-universal.desktop",
        "spider-os-workspace-max.desktop",
    ),
    "dev-bay": (
        "virt-manager.desktop",
    ),
}

# Every exact ID is unique. User-selected placements still override these
# recommendations through app-placement.json.
EXACT_BAYS = {
    ident.casefold(): bay
    for bay, entries in UBUNTU_STUDIO_DESKTOP_IDS.items()
    for ident in entries
}

# Exact-ish token/phrase matching avoids a word inside another word being
# mistaken for an app. Priorities explicitly separate creation from playback.
KNOWN_APPLICATIONS = (
    ("webbie", ("spider webbie", "webbie", "webby intelligence center")),
    ("deep-forage", ("deep forage", "deep-forage")),
    ("forage", ("forage",)),
    ("kali-bay", ("kali bay", "kali-bay")),
    ("studio", ("spider studio", "spider-studio",
       "aeolus", "zita-at1", "zita-rev1", "zita-mu1", "dgEdit",
       "ffado mixer studio", "fluidsynth", "jack mixer", "jack_mixer",
       "jacktrip", "patchance", "phaseX", "freewheeling",
       "setbfree", "sooperlooper", "fmit", "hexter", "xjadeo",
       "qprompt", "devedeng", "devede", "recorder", "meterbridge",
       "qlcplus", "q light controller plus",
       "ardour", "qtractor", "reaper", "audacity", "mixxx",
       "hydrogen", "rosegarden", "musescore", "guitarix", "rakarrack",
       "carla", "cadence", "catia", "claudia", "agordejo", "raysession",
       "ray session", "helm", "yoshimi", "zynaddsubfx", "zrythm",
       "synthv1", "samplv1", "drumkv1", "padthv1", "qsynth", "qjackctl",
       "patchage", "jack keyboard", "qpwgraph", "helvum", "easyeffects",
       "calf", "lsp plugin", "kdenlive", "shotcut", "openshot",
       "olive editor", "olive video", "obs studio", "obs-studio",
       "obsidian video", "handbrake", "k3b", "brasero")),
    ("media", ("internet dj console", "kid3", "freeShow", "openlp", "vlc", "audacious", "mpv", "smplayer", "dragon player",
       "elisa", "rhythmbox", "strawberry", "clementine", "haruna",
       "parole", "steam", "lutris", "retroarch", "spider media center")),
    ("art-lab", ("spectacle", "color profile viewer", "krita", "gimp", "inkscape", "blender", "darktable",
       "digikam", "rawtherapee", "scribus", "fontforge", "mypaint",
       "pencil2d", "synfig", "freecad", "kcolorchooser", "kolourpaint")),
    ("author", ("author", "libreoffice writer", "writer", "focuswriter", "scribus writer",
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
    ("devices", ("hdajackretask", "envy24", "mudita24", "hdspmixer",
       "hdspconf", "qasconfig", "qashctl", "qasmixer", "ffado mixer",
       "wacom tablet finder", "kde qrca", "bluetooth", "kdeconnect", "kde connect", "partitionmanager",
       "partition manager", "gparted", "gsmartcontrol", "pavucontrol",
       "pulse audio volume control", "input-remapper", "usbview",
       "usb creator", "usb-creator", "kde partition manager")),
    ("system", ("timeshift", "backintime", "back in time", "spider guardian",
       "spider vault", "discover", "synaptic", "software updater",
       "system settings", "systemsettings", "grub customizer")),
)


def _has_name(identity, term):
    import re
    return bool(re.search(r"(?<![a-z0-9])" + re.escape(term.casefold()) +
                          r"(?![a-z0-9])", identity.casefold()))


def workspace_for(desktop_id, name, categories):
    """Choose one PRIMARY bay, without removing an app from global search."""
    matched = EXACT_BAYS.get(str(desktop_id).casefold())
    if matched is not None:
        return matched
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


# Specific, visible in-bay explanations. No application is launched simply
# to generate this description or to discover whether it was installed.
APP_TASKS = (
    ("spider studio", "Use the native Spider Studio workspace. The original desktop entry remains available as a fallback."),
    ("spider media center", "Open your existing Spider Media Center and BCN listening/broadcast interface."),
    ("internet dj console", "Operate a live Internet radio DJ console for microphones, music and broadcast feeds."),
    ("aeolus", "Play an organ-style software instrument from your keyboard or MIDI controls."),
    ("zita-at1", "Use a pitch-correction audio processor during instrument or vocal production."),
    ("dgedit", "Edit sampled instrument definitions and soundfont-like percussion mappings."),
    ("din", "Experiment with continuous tones, drones and software synthesis."),
    ("fluidsynth dssi", "Use a SoundFont synthesizer plugin for MIDI playback."),
    ("freewheeling", "Record and layer live audio loops for improvisation."),
    ("jack mixer", "Mix JACK-connected audio signals in a software mixer."),
    ("jack_mixer", "Mix JACK-connected audio signals in a software mixer."),
    ("ffado mixer", "Inspect and control supported FireWire audio-interface mixers."),
    ("envy24 control", "Manage supported Envy24 audio-interface mixer settings."),
    ("hdspmixer", "Inspect a supported RME HDSP interface mixer."),
    ("hdspconf", "Inspect supported RME HDSP hardware configuration."),
    ("hdajackretask", "Inspect and configure supported audio jack assignments."),
    ("mudita24", "Manage supported multichannel ALSA sound-card routing."),
    ("qasconfig", "Inspect ALSA audio hardware configuration."),
    ("qashctl", "Inspect ALSA audio hardware controls."),
    ("qasmixer", "Mix supported ALSA device channels."),
    ("kid3", "Edit music metadata and album tags without changing the underlying recording artist rules."),
    ("geonkick", "Design synthesized percussion and build drum sounds."),
    ("drumkv1", "Program a sample-based drum instrument."),
    ("jack keyboard", "Play MIDI notes through a virtual keyboard into connected instruments."),
    ("virtual midi keyboard", "Play musical notes through a virtual MIDI keyboard."),
    ("vmpk", "Play and test MIDI instruments from an on-screen piano keyboard."),
    ("guitarix", "Use virtual guitar amplifiers and effects."),
    ("padthv1", "Play a polyphonic pad synthesizer for layered music."),
    ("samplv1", "Use a sampled instrument driven by MIDI notes."),
    ("synthv1", "Play a subtractive MIDI synthesizer."),
    ("qsynth", "Control a FluidSynth soundfont synthesizer."),
    ("sooperlooper", "Record and manipulate live audio loops while producing music."),
    ("ph asex", "Design synthesizer patches and sounds."),
    ("phasex", "Design synthesizer patches and sounds."),
    ("q light controller plus", "Plan and operate stage lighting in a live production."),
    ("qlcplus", "Plan and operate stage lighting in a live production."),
    ("qprompt", "Read scripts from a teleprompter while recording video or presenting."),
    ("openlp", "Prepare presentation and projection content for live shows."),
    ("freeshow", "Build visuals and presentation scenes for events or streams."),
    ("xjadeo", "Synchronize video reference playback with audio production."),
    ("recorder", "Capture microphone audio into a recording."),
    ("fmit", "Tune instruments using a pitch-detection interface."),
    ("webbie: connect onedrive", "Connect Webbie's Study/Author file-sync workflow after owner approval."),
    ("webbie: sleep quietly", "Put Webbie's floating face into quiet mode without stopping her background services."),
    ("webbie: wake face", "Return Webbie's animated face to its active display."),
    ("deep forage", "Explore advanced research and compare evidence inside the existing native bay."),
    ("kali-bay", "Open the existing isolated Kali workspace for authorized defensive security."),
    ("forage", "Gather and compare research sources inside the existing native Forage bay."),
    ("author", "Open the existing native Author workspace for manuscripts and continuity work."),
    ("ardour", "Record and arrange multitrack audio, edit takes, mix sessions and export masters."),
    ("qtractor", "Arrange MIDI and audio tracks in a Linux recording session."),
    ("audacity", "Edit and clean up individual WAV recordings and voice tracks."),
    ("carla", "Host instruments and audio-effect plugins inside Studio."),
    ("qjackctl", "Inspect and route JACK audio and MIDI connections."),
    ("qpwgraph", "Inspect and connect PipeWire audio and video nodes."),
    ("helvum", "Connect PipeWire streams in a patchbay-style view."),
    ("hydrogen", "Build drum patterns, rhythm sections and percussion demos."),
    ("mixxx", "DJ with decks and cueing for sets and live shows."),
    ("musescore", "Write, play back and print sheet music and arrangements."),
    ("rosegarden", "Compose and edit MIDI scores and orchestrations."),
    ("yoshimi", "Design and play synthesizer sounds."),
    ("guitarix", "Use guitar amplifiers and effects for recording."),
    ("easyeffects", "Apply effects and processing to PipeWire audio."),
    ("kdenlive", "Edit multitrack video, sound, transitions and titles."),
    ("shotcut", "Cut and render edited video."),
    ("openshot", "Assemble video clips and basic motion graphics."),
    ("obs studio", "Record the screen, webcam and media for a video or live stream."),
    ("obs-studio", "Record the screen, webcam and media for a video or live stream."),
    ("handbrake", "Transcode video into compatible playback formats."),
    ("blender", "Build and render 3D sets, city scenes, objects and animation."),
    ("krita", "Paint character art, backgrounds and cinematic concept illustrations."),
    ("gimp", "Retouch photographs, composite images and edit raster artwork."),
    ("inkscape", "Design scalable logos, maps, icons and vector graphics."),
    ("darktable", "Develop and color-grade RAW photographs."),
    ("digikam", "Organize and review photographic libraries."),
    ("scribus", "Lay out multi-page printable documents and publishing artwork."),
    ("libreoffice writer", "Write and format essays, manuscripts and DOCX documents."),
    ("focuswriter", "Write prose in a distraction-free editor."),
    ("ghostwriter", "Draft Markdown text and long-form writing."),
    ("libreoffice calc", "Work with spreadsheets, formulas and budgets."),
    ("libreoffice impress", "Create presentation slides."),
    ("okular", "Read and annotate PDFs and reference documents."),
    ("thunderbird", "Read, draft and send email in your connected mail account."),
    ("firefox", "Browse websites, verify sources and use online services."),
    ("konsole", "Run terminal commands and inspect local system processes."),
    ("kate", "Edit code, scripts and text with syntax highlighting."),
    ("kdevelop", "Work on software projects with an IDE."),
    ("kde connect", "Pair compatible devices for transfers and shared controls."),
    ("kdeconnect", "Pair compatible devices for transfers and shared controls."),
    ("partition manager", "Inspect partitions with graphical disk-management tools. Changes require explicit approval."),
    ("partitionmanager", "Inspect partitions with graphical disk-management tools. Changes require explicit approval."),
    ("timeshift", "Inspect or manage system restore snapshots."),
    ("backintime", "Review backed-up versions of personal files."),
    ("vlc", "Play local video, audio and compatible network streams."),
    ("mpv", "Play video and audio with a lightweight media player."),
    ("steam", "Run installed games without moving game files into a different workspace."),
    ("wireshark", "Review captured packets in authorized network investigations."),
    ("nmap", "Inspect networks and hosts only with explicit authorization."),
)


def app_purpose(app):
    """Answer 'why do I need this installed app?' in its actual native bay."""
    identity = (app.desktop_id + " " + app.name).casefold()
    for token, explanation in APP_TASKS:
        if _has_name(identity, token):
            return explanation
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
