#!/usr/bin/env python3
"""Brand KDE's secure locker; preserve its authentication implementation."""
from pathlib import Path
import os
import shutil
import subprocess

writer = shutil.which('kwriteconfig6') or shutil.which('kwriteconfig5')
if not writer:
    raise SystemExit('KDE configuration writer is unavailable.')
wallpaper = Path('/usr/local/lib/spider-os/branding/splash/spider-os-splash.png')
if not wallpaper.is_file():
    raise SystemExit('Spider lock-screen artwork is missing.')
config = Path(os.environ.get('XDG_CONFIG_HOME', Path.home() / '.config')) / 'kscreenlockerrc'
backup = config.with_name('kscreenlockerrc.before-the-web')
if config.exists() and not backup.exists():
    shutil.copyfile(config, backup)
subprocess.run([writer, '--file', str(config), '--group', 'Greeter', '--key', 'WallpaperPlugin', 'org.kde.image'], check=True)
subprocess.run([writer, '--file', str(config), '--group', 'Greeter', '--group', 'Wallpaper', '--group', 'org.kde.image', '--group', 'General', '--key', 'Image', wallpaper.as_uri()], check=True)
print('Spider lock-screen artwork applied. KDE still handles secure locking and authentication.')
