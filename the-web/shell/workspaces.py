"""Load Spider's own Qt workspaces into tabs with isolated module namespaces."""
import importlib.util
import sys
import types
from pathlib import Path

NATIVE = {
    'author': ('author', 'main.py', 'AuthorWindow'),
    'studio': ('studio', 'main.py', 'SpiderStudio'),
    'study': ('study', 'study.py', 'StudyWindow'),
    'forage': ('forage', 'forage.py', 'ForageWindow'),
    'deep-forage': ('forage', 'deep-forage/deep_forage.py', 'DeepForageWindow'),
    'kali-bay': ('kali-bay/ui', 'kali_bay.py', 'KaliBayWindow'),
    'webbie': ('webbie/ui', 'webbie-ui.py', 'WebbieWindow'),
}

def create_native(workspace, root):
    if workspace not in NATIVE: return None
    directory, file, class_name = NATIVE[workspace]
    location = Path(root) / directory
    namespace = '_spider_workspace_' + directory.replace('/', '_').replace('-', '_')
    if namespace not in sys.modules:
        package = types.ModuleType(namespace); package.__path__ = [str(location)]
        sys.modules[namespace] = package
    name = namespace + '.' + workspace.replace('-', '_')
    if name not in sys.modules:
        spec = importlib.util.spec_from_file_location(name, location / file)
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        try: spec.loader.exec_module(module)
        except Exception:
            sys.modules.pop(name, None)
            raise
    return getattr(sys.modules[name], class_name)()
