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
print('SPIDER_QT: construct The Web', flush=True)
window = main.TheWeb()
assert window.background_picker.count() == 10
for index in range(10):
    name = window.background_picker.itemData(index)
    print(f'SPIDER_QT: background {name}', flush=True)
    image = main.WALLPAPER if name == 'default' else root / 'branding' / 'workspaces' / f'{name}.png'
    assert image.is_file(), f'Missing background: {image}'
    window.background_picker.setCurrentIndex(index)
    assert window.wallpaper is not None and not window.wallpaper.isNull(), name
    app.processEvents()
print('SPIDER_QT: close', flush=True)
window.close()
app.processEvents()
faulthandler.cancel_dump_traceback_later()
print('SPIDER_QT: PASSED', flush=True)
