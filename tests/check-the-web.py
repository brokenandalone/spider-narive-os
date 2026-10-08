"""Exercise the installed shell and every background with bounded diagnostics."""
import faulthandler
from pathlib import Path
import sys

faulthandler.enable()
faulthandler.dump_traceback_later(30, repeat=True)
root = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(root / 'the-web' / 'shell'))
print('SPIDER_QT: import', flush=True)
from PyQt5.QtWidgets import QApplication
import main

# Also supports testing the identical payload in a checkout.
main.SPIDER_ROOT = root
main.WALLPAPER = root / 'branding' / 'wallpapers' / 'spider-os-wallpaper.png'
print('SPIDER_QT: application', flush=True)
app = QApplication([])
# Regression: the actual visible central widget must render the image.
from PyQt5.QtGui import QColor, QPixmap
surface = main.WallpaperWidget()
surface.resize(120, 80)
red = QPixmap(20, 20); red.fill(QColor(255, 0, 0))
blue = QPixmap(20, 20); blue.fill(QColor(0, 0, 255))
surface.set_background(red)
red_pixel = surface.grab().toImage().pixelColor(4, 4)
surface.set_background(blue)
blue_pixel = surface.grab().toImage().pixelColor(4, 4)
assert red_pixel.red() > red_pixel.blue(), red_pixel.name()
assert blue_pixel.blue() > blue_pixel.red(), blue_pixel.name()
surface.close()
print('SPIDER_QT: construct The Web', flush=True)
window = main.TheWeb()
assert isinstance(window.centralWidget(), main.WallpaperWidget)
assert window.background_picker.count() == 11
for index in range(11):
    name = window.background_picker.itemData(index)
    print(f'SPIDER_QT: background {name}', flush=True)
    image = main.WALLPAPER if name == 'default' else root / 'branding' / 'workspaces' / f'{main.WORKSPACE_IMAGES.get(name, name)}.png'
    assert image.is_file(), f'Missing background: {image}'
    window.background_picker.setCurrentIndex(index)
    assert window.wallpaper is not None and not window.wallpaper.isNull(), name
    app.processEvents()
# Native Studio should construct even if optional apps and system services are absent.
import importlib.util
spec = importlib.util.spec_from_file_location('studio_ui', root / 'studio/main.py')
studio = importlib.util.module_from_spec(spec)
spec.loader.exec_module(studio)
from unittest.mock import patch
import tempfile
with patch.object(main, 'media_command', side_effect=main.AppUnavailable('media missing')):
    window.open_media()
    assert window.status.text() == 'media missing'
with patch.object(main.subprocess, 'Popen') as process:
    window.open_studio()
    assert process.call_args.args[0] == ['python3', str(root / 'studio/main.py')]
with tempfile.TemporaryDirectory() as folder:
    with patch.object(main, 'AUTHOR_HOME', Path(folder) / 'Author'), \
         patch.object(main, 'author_command', return_value=['kate', '--start', 'Spider-Author']), \
         patch.object(main.subprocess, 'Popen') as process:
        window.open_author()
        assert window.background_picker.currentData() == 'author'
        assert process.call_args.kwargs['cwd'] == Path(folder) / 'Author'
    with patch.object(studio, 'STUDIO_HOME', Path(folder) / 'Studio'):
        studio_window = studio.SpiderStudio()
        assert not (Path(folder) / 'Studio/Author').exists()
        assert studio_window.windowTitle() == 'Spider Studio | Spider OS'
        with patch.object(studio.shutil, 'which', return_value=None):
            studio_window.launch_music()
            assert 'No supported DAW' in studio_window.status.text()
        studio_window.close()
        app.processEvents()
print('SPIDER_QT: Forage source-link rendering', flush=True)
spec = importlib.util.spec_from_file_location('forage_ui', root / 'forage/forage.py')
forage = importlib.util.module_from_spec(spec)
spec.loader.exec_module(forage)
search_window = forage.ForageWindow()
search_window.show_results('local', 'river', [{'path': '/tmp/example.md', 'url': 'file:///tmp/example.md',
    'title': '<script>', 'snippet': 'river text', 'stale': True}])
assert 'file:///tmp/example.md' in search_window.results.toHtml()
assert 'Source changed since indexing' in search_window.results.toPlainText()
assert '<script>' in search_window.results.toPlainText()
search_window.close()
print('SPIDER_QT: close', flush=True)
window.close()
app.processEvents()
faulthandler.cancel_dump_traceback_later()
print('SPIDER_QT: PASSED', flush=True)
