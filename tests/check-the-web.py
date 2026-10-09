"""Offscreen native desktop integration: real tabs, state, edits and safe close."""
import os
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch
root = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / 'the-web/shell'))
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QColor,QPixmap
from PyQt5.QtCore import Qt
import main
main.SPIDER_ROOT = root
from app_catalog import InstalledApp

app=QApplication([])
with tempfile.TemporaryDirectory() as folder, patch('pathlib.Path.home',return_value=Path(folder)), patch.dict(os.environ,{'XDG_CONFIG_HOME':folder}), patch.object(main.TheWeb,'refresh_status'):
    surface=main.WallpaperWidget();surface.resize(120,80)
    for color in ['red','blue']:
        pixmap=QPixmap(20,20);pixmap.fill(QColor(color));surface.set_background(pixmap)
        pixel=surface.grab().toImage().pixelColor(4,4)
        assert (pixel.red()>pixel.blue()) == (color=='red')
    surface.close()
    window=main.TheWeb(restore=False);window.show()
    for name in main.WORKSPACES:
        window.open_workspace(name)
        assert not window.wallpaper.isNull(),name
    assert window.tabs.count()==15
    for name in ['system', 'recovery']:
        panel = window.workspace_widgets[name].native
        assert panel is not None and panel.tables['storage'].rowCount() > 0
        assert panel.tables['backups'].columnCount() == 3
        with patch('system_panel.collect', return_value={'services': [], 'audio': 'PipeWire test', 'checkedAt': '12:00:00'}):
            panel.refresh()
            assert panel.worker.wait(3000)
            app.processEvents()
            assert panel.audio.toPlainText() == 'PipeWire test'
            assert panel.refresh_button.isEnabled()
    author=window.workspace_widgets['author'].native
    window.open_author();window.open_author();assert window.workspace_widgets['author'].native is author
    assert window.tabs.count()==15
    for name in ['author','study','studio','forage','deep-forage','webbie','kali-bay']:
        assert window.workspace_widgets[name].native is not None,name
    book=author.store.create_book('Desktop test');chapter=author.store.create_chapter(book,'One','Original')
    author.load_books();author.books.setCurrentRow(0);author.chapters.setCurrentRow(0)
    author.editor.setPlainText('Edited inside the workspace tab');assert author.flush()
    author_index=window.tabs.indexOf(window.workspace_widgets['author'])
    with patch.object(author,'flush',return_value=False):
        window.close_tab(author_index);assert 'author' in window.workspace_widgets
        assert not window.close()
    worker=window.workspace_widgets['forage'].native
    with patch.object(worker,'worker') as busy:
        busy.isRunning.return_value=True
        window.close_tab(window.tabs.indexOf(window.workspace_widgets['forage']))
        assert 'forage' in window.workspace_widgets
    school=window.workspace_widgets['study'].native
    with patch.object(school,'save_notes',side_effect=OSError('disk full')):
        window.close_tab(window.tabs.indexOf(window.workspace_widgets['study']));assert 'study' in window.workspace_widgets
    fake=InstalledApp('ardour.desktop',Path('/tmp/Ardour.desktop'),'Ardour','Record','ardour','studio')
    window.installed_apps=[fake];window.start_menu.populate()
    window.start_menu.search.setText('ardour');assert window.start_menu.results.count()==1
    with patch.object(main,'launch_command',return_value=['gio','launch',str(fake.path)]),patch.object(main.subprocess,'Popen') as process, patch.object(main,'wm_command') as wm:
        # Exercise real desktop code paths: launching Firefox-like XDG apps must
        # never turn on KDE Show Desktop and hide the newly opened window.
        window.desktop_mode=True
        window.open_installed(fake.desktop_id)
        window.desktop_mode=False
        assert process.call_args.args[0]==['gio','launch',str(fake.path)]
        assert window.current_workspace=='studio'
        wm.assert_not_called()
    # Workspace Files opens the user's real project directory through the
    # desktop file manager without any data copy or destructive operation.
    with patch.object(main, 'file_open_command', return_value=['xdg-open', '/home/test/Documents/Spider Studio']), patch.object(main.subprocess, 'Popen') as folder_open:
        window.open_workspace_folder('/home/test/Documents/Spider Studio', 'studio')
        assert folder_open.call_args.args[0] == ['xdg-open', '/home/test/Documents/Spider Studio']
        assert window.current_workspace == 'studio'
    window.open_workspace('deep-forage')
    wallpaper_id=window.wallpaper_catalog.defaults['deep-forage']
    window.wallpaper_picker.setCurrentIndex(window.wallpaper_picker.findData(wallpaper_id))
    window.open_author();assert window.close()
    reopened=main.TheWeb();assert reopened.tabs.count()==15;assert reopened.current_workspace=='author'
    assert reopened.workspace_widgets['author'].native.store.chapter(chapter)['content']=='Edited inside the workspace tab'
    assert reopened.wallpaper_catalog.selected_id('deep-forage')==wallpaper_id
    assert reopened.close();app.processEvents()
print('DESKTOP INTEGRATION PASSED: 15 tabs, seven native workspaces, saved editing/state/wallpapers, installed-app launching and safe close')
