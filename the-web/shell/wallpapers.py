"""Packaged wallpaper catalog and per-workspace user choices."""
import json
import os
from pathlib import Path


class WallpaperCatalog:
    def __init__(self, root, config_home=None):
        self.root = Path(root).resolve()
        self.config = Path(config_home or os.environ.get('XDG_CONFIG_HOME', Path.home() / '.config')) / 'spider-os' / 'wallpapers.json'
        try:
            data = json.loads((self.root / 'branding/wallpapers/collection.json').read_text())
        except (OSError, ValueError):
            data = {}
        self.entries = []
        for entry in data.get('wallpapers', []):
            path = (self.root / entry['file']).resolve()
            if path.is_relative_to(self.root) and path.is_file():
                self.entries.append(entry)
        self.by_id = {e['id']: e for e in self.entries}
        self.defaults = data.get('new_workspace_defaults', {})
        try:
            self.choices = json.loads(self.config.read_text())
            if not isinstance(self.choices, dict):
                self.choices = {}
        except (OSError, ValueError):
            self.choices = {}

    def original(self, workspace):
        if workspace == 'default':
            return self.root / 'branding/wallpapers/spider-os-wallpaper.png'
        image = self.root / 'branding/workspaces' / (workspace + '.png')
        if workspace == 'author' and not image.exists():
            image = self.root / 'branding/workspaces/system.png'
        return image

    def selected_id(self, workspace):
        choice = self.choices.get(workspace)
        if isinstance(choice, str) and (choice == 'original' or choice in self.by_id):
            return choice
        if self.original(workspace).exists():
            return 'original'
        return self.defaults.get(workspace, 'original')

    def path(self, workspace):
        entry = self.by_id.get(self.selected_id(workspace))
        path = self.root / entry['file'] if entry else self.original(workspace)
        return path if path.exists() else self.original('default')

    def select(self, workspace, ident):
        if ident != 'original' and ident not in self.by_id:
            raise ValueError('Unknown wallpaper')
        choices = dict(self.choices, **{workspace: ident})
        self.config.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.config.with_suffix('.tmp')
        temporary.write_text(json.dumps(choices, indent=2) + '\n')
        temporary.replace(self.config)
        self.choices = choices
