"""Offscreen native desktop integration: real tabs, state, edits and safe close."""
import os
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch
root = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / 'the-web/shell'))
from PyQt5.QtWidgets import QApplication, QPushButton
from PyQt5.QtGui import QColor,QPixmap
from PyQt5.QtCore import Qt
import main
main.SPIDER_ROOT = root
from app_catalog import InstalledApp
from desktop import Task

app=QApplication([])
with tempfile.TemporaryDirectory() as folder, patch('pathlib.Path.home',return_value=Path(folder)), patch.dict(os.environ,{'XDG_CONFIG_HOME':folder}), patch.object(main.TheWeb,'refresh_status'):
    surface=main.WallpaperWidget();surface.resize(120,80)
    for color in ['red','blue']:
        pixmap=QPixmap(20,20);pixmap.fill(QColor(color));surface.set_background(pixmap)
        pixel=surface.grab().toImage().pixelColor(4,4)
        assert (pixel.red()>pixel.blue()) == (color=='red')
    surface.close()
    window=main.TheWeb(restore=False);window.show()
    # Appearance is a user-chosen shell preference, not a KDE/GTK mutation.
    # Keep the original wallpaper catalog and all native Author data intact.
    assert window.appearance=='dark'
    assert 'color:#f5eff8' in window.styleSheet()
    assert window.taskbar.styleSheet()==window.styleSheet()
    window.choose_appearance('light')
    assert window.appearance=='light'
    assert 'color:#241332' in window.styleSheet()
    assert window.background_surface.appearance=='light'
    assert window.taskbar.styleSheet()==window.styleSheet()
    assert window.start_menu.styleSheet()==window.styleSheet()
    assert (Path(folder)/'spider-os/appearance.json').is_file()
    with patch.object(main, 'list_tasks', return_value=[Task('0x00000101', 'Movie'), Task('0x00000102', 'Editor'), Task('0x00000103', 'Browser')]), patch.object(main, 'close_window') as close, patch.object(main.QApplication, 'primaryScreen') as screen, patch.object(main, 'minimize_window', return_value=True) as minimize, patch.object(main, 'maximize_window') as maximize:
        screen.return_value.geometry.return_value.width.return_value = 1280
        # October 11 taskbar discovery is asynchronous. Render a mocked
        # immutable scan result directly so this GUI smoke remains deterministic
        # while still exercising close, menus, minimize, maximize and overflow.
        task_snapshot = [Task('0x00000101', 'Movie'),
                         Task('0x00000102', 'Editor'),
                         Task('0x00000103', 'Browser')]
        window.desktop_mode = True
        window.taskbar.render_tasks(task_snapshot)
        group = window.taskbar.tasks.itemAt(0).widget()
        close_button = next(item for item in group.findChildren(QPushButton) if item.text() == '×')
        close_button.click(); close.assert_called_with('0x00000101')
        overflow = window.taskbar.tasks.itemAt(2).widget().menu()
        overflow.actions()[0].menu().actions()[1].trigger()
        close.assert_called_with('0x00000103')
        overflow.actions()[0].menu().actions()[2].trigger(); minimize.assert_called_with('0x00000103')
        overflow.actions()[0].menu().actions()[3].trigger(); maximize.assert_called_with('0x00000103')
        screen.return_value.geometry.return_value.width.return_value = 900
        window.taskbar.render_tasks(task_snapshot); assert window.taskbar.tasks.itemAt(0).widget().menu() is not None
        window.desktop_mode = False; window.taskbar.render_tasks([])
    for name in main.WORKSPACES:
        window.open_workspace(name)
        assert not window.wallpaper.isNull(),name
    assert window.tabs.count()==len(main.WORKSPACES)
    for bay, widget in (
        ('devices', main.DevicesPanel),
        ('productivity', main.ProductivityPanel),
        ('art-lab', main.ArtLabPanel),
        ('communications', main.CommunicationsPanel),
        ('dev-bay', main.DevBayPanel),
    ):
        assert isinstance(window.workspace_widgets[bay].native, widget), bay
    for bay in main.WORKSPACES:
        if bay == 'default':
            continue
        assert isinstance(window.workspace_widgets[bay].mission_desk, main.BayMissionPanel), bay
    studio_rack = window.workspace_widgets['studio'].instrument_rack
    assert isinstance(studio_rack, main.InstrumentRack)
    assert studio_rack.mode.count() == 4
    assert len(studio_rack.steps['Kick']) == 16
    studio_rack.mode.setCurrentText('Drums')
    assert studio_rack.drums_group.isVisible()
    assert studio_rack.wav().startswith(b'RIFF')
    studio_rack.mode.setCurrentText('Guitar')
    assert studio_rack.wav('E').startswith(b'RIFF')
    webbie_operations = window.workspace_widgets['webbie'].webbie_operations
    assert isinstance(webbie_operations, main.WebbieNativeOperations)
    assert webbie_operations.tabs.count() == 3
    assert webbie_operations.cognitive is not None
    assert webbie_operations.missions is not None
    assert webbie_operations.workflow is not None
    assert webbie_operations.can_close()
    # Legacy control-center launchers route into existing native bays;
    # no subprocess is ever spawned and Ubuntu Studio entries stay intact.
    with patch.object(window, 'launch') as legacy_launch:
        window.open_installed('spider-webbie-intelligence.desktop')
        assert window.current_workspace == 'webbie'
        assert window.workspace_widgets['webbie'].workspace_tabs.tabText(
            window.workspace_widgets['webbie'].workspace_tabs.currentIndex()
        ) == 'Webbie controls'
        window.open_installed('spider-os-workspace-max.desktop')
        assert window.current_workspace == 'default'
        legacy_launch.assert_not_called()
    research = window.workspace_widgets['webbie'].findChildren(main.WebbieResearchPanel)
    assert len(research) == 1, 'Webbie research mind not present in native bay'
    mission_store = window.workspace_widgets['studio'].mission_desk.store
    saved = mission_store.add('studio', 'Mix session for Qt integration test')
    assert any(m['id'] == saved['id'] for m in mission_store.for_bay('studio'))
    mission_store.update(saved['id'], destination='productivity', status='active')
    assert any(m['id'] == saved['id'] for m in mission_store.for_bay('productivity'))
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
    media_panel = window.workspace_widgets['media'].native
    with patch('media_panel.discover_players', return_value=['org.mpris.MediaPlayer2.vlc']), patch('media_panel.player_state', return_value='Paused'), patch('media_panel.control') as transport:
        media_panel.refresh(); assert media_panel.worker.wait(3000); app.processEvents()
        assert not media_panel.controls[0].isEnabled()
        media_panel.players.setCurrentIndex(1); media_panel.refresh('PlayPause')
        assert media_panel.worker.wait(3000); app.processEvents()
        transport.assert_called_once_with('org.mpris.MediaPlayer2.vlc', 'PlayPause')
        assert media_panel.status.text() == 'Paused' and media_panel.controls[0].isEnabled()
    system = window.workspace_widgets['system'].native
    with patch('system_panel.adjust_audio') as audio_change, patch('system_panel.collect', return_value={'volume': 'Output: 45%', 'services': []}):
        system.change_audio('Up'); assert system.worker.wait(3000); app.processEvents()
        audio_change.assert_called_once_with('Up'); assert system.volume.text() == 'Output: 45%'
        assert all(button.isEnabled() for button in system.audio_buttons)
    window.open_audio(); assert system.tabs.currentWidget() is system.audio_page
    author=window.workspace_widgets['author'].native
    window.open_author();window.open_author();assert window.workspace_widgets['author'].native is author
    assert window.tabs.count()==len(main.WORKSPACES)
    for name in ['author','study','studio','forage','deep-forage','webbie','kali-bay']:
        assert window.workspace_widgets[name].native is not None, (name, getattr(window.workspace_widgets[name], 'native_error', 'no error detail'))
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
    # All installed programs stay reachable, even if the primary bay differs.
    krita = InstalledApp('krita.desktop', Path('/tmp/Krita.desktop'),
                         'Krita', 'Paint artwork', 'krita', 'art-lab')
    window.installed_apps = [fake, krita]
    window.populate_app_list('studio')
    assert window.app_lists['studio'].count() == 1
    window.app_scopes['studio'].setCurrentIndex(1)
    assert window.app_lists['studio'].count() == 2
    window.app_queries['studio'].setText('krita')
    assert window.app_lists['studio'].count() == 1
    assert window.app_lists['studio'].item(0).data(Qt.UserRole) == 'krita.desktop'
    window.app_lists['studio'].setCurrentRow(0)
    with (patch.object(main, 'save_app_assignment') as save,
          patch.object(window, 'refresh_apps') as refresh):
        window.assign_selected_app('studio')
        save.assert_called_once_with('krita.desktop', 'studio')
        refresh.assert_called_once()
    window.app_queries['studio'].clear()
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
    reopened=main.TheWeb();assert reopened.tabs.count()==len(main.WORKSPACES);assert reopened.current_workspace=='author'
    assert reopened.appearance=='light'
    assert reopened.background_surface.appearance=='light'
    assert reopened.taskbar.styleSheet()==reopened.styleSheet()
    assert reopened.workspace_widgets['author'].native.store.chapter(chapter)['content']=='Edited inside the workspace tab'
    assert reopened.wallpaper_catalog.selected_id('deep-forage')==wallpaper_id
    assert reopened.close();app.processEvents()
print('DESKTOP INTEGRATION PASSED: full native bay registry, project workbenches, saved editing/state/wallpapers and safe close')
