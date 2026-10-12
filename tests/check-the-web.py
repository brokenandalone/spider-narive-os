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
        window.desktop_mode = True
        window.taskbar.render_tasks([Task('0x00000101', 'Movie'), Task('0x00000102', 'Editor'), Task('0x00000103', 'Browser')])
        # Quick Launch may activate only IDs in the current scanned X11 list.
        window.command_palette.search.setText('Movie')
        assert any(window.command_palette.matches.item(i).data(Qt.UserRole)
                   == ('window', '0x00000101')
                   for i in range(window.command_palette.matches.count()))
        with patch.object(main, 'wm_command') as requested:
            window.activate_launcher_window('0x00000101')
            requested.assert_called_once_with('-i', '-a', '0x00000101')
            window.activate_launcher_window('0xDEADBEEF')
            requested.assert_called_once()
        group = window.taskbar.tasks.itemAt(0).widget()
        close_button = next(item for item in group.findChildren(QPushButton) if item.text() == '×')
        close_button.click(); close.assert_called_with('0x00000101')
        overflow = window.taskbar.tasks.itemAt(2).widget().menu()
        overflow.actions()[0].menu().actions()[1].trigger()
        close.assert_called_with('0x00000103')
        overflow.actions()[0].menu().actions()[2].trigger(); minimize.assert_called_with('0x00000103')
        overflow.actions()[0].menu().actions()[3].trigger(); maximize.assert_called_with('0x00000103')
        screen.return_value.geometry.return_value.width.return_value = 900
        window.taskbar.render_tasks([Task('0x00000101', 'Movie'), Task('0x00000102', 'Editor'), Task('0x00000103', 'Browser')]); assert window.taskbar.tasks.itemAt(0).widget().menu() is not None
        window.desktop_mode = False; window.taskbar.render_tasks([])
    # Launcher search is a visible, fixed-target UI, never a shell interpreter.
    window.command_palette.search.setText('Webbie')
    assert any(window.command_palette.matches.item(i).data(Qt.UserRole) == ('workspace', 'webbie')
               for i in range(window.command_palette.matches.count()))
    window.command_palette.search.setText('Studio')
    window.command_palette.refresh()
    assert window.command_palette.matches.count() >= 1
    window.command_palette.hide()
    # A broken native workspace must leave a usable recovery surface and
    # recover on explicit retry, not on a timer or Webbie request.
    with patch.object(main, 'create_native', side_effect=RuntimeError('simulated native load failure')):
        window.open_workspace('study')
        assert 'study' in window.workspace_load_errors
        assert window.workspace_widgets['study'].native is None
    window.retry_workspace('study')
    assert 'study' not in window.workspace_load_errors
    assert window.workspace_widgets['study'].native is not None
    for name in main.WORKSPACES:
        window.open_workspace(name)
        assert not window.wallpaper.isNull(),name
    assert window.tabs.count()==15
    # Workspace tabs can be reordered without displacing the permanent home.
    window.tabs.tabBar().moveTab(0, 3)
    assert window.tabs.indexOf(window.workspace_widgets['default']) == 0
    study_index = window.tabs.indexOf(window.workspace_widgets['study'])
    window.tabs.tabBar().moveTab(study_index, 1)
    assert window.tabs.indexOf(window.workspace_widgets['study']) == 1
    window.tabs.setCurrentIndex(0)
    window.cycle_tab(1)
    assert window.tabs.currentWidget() is window.workspace_widgets['study']
    window.cycle_tab(-1)
    assert window.tabs.currentWidget() is window.workspace_widgets['default']
    assert 'Open workspace tabs:' in window.webbie_assistant.workspace_summary
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
    assert window.navigation_state['recent']
    window.clear_recent_navigation()
    assert not window.navigation_state['recent']
    assert not main.load_navigation(window.navigation_path, main.WORKSPACES)['recent']
    window.open_workspace('deep-forage')
    wallpaper_id=window.wallpaper_catalog.defaults['deep-forage']
    window.wallpaper_picker.setCurrentIndex(window.wallpaper_picker.findData(wallpaper_id))
    # Off-thread app and wmctrl discovery must finish before tearing down Qt.
    app.processEvents()
    for active in (window.app_scan_worker, window.taskbar.window_scan_worker):
        if active is not None and active.isRunning():
            assert active.wait(10000)
    app.processEvents()
    window.open_author()
    checkpoint = window.save_layout_checkpoint()
    assert checkpoint['active'] == 'author'
    assert checkpoint['open'][0] == 'default'
    assert window.restore_layout_checkpoint()
    assert window.current_workspace == 'author'
    from desktop_service_health import ServiceHealth
    sample_services = [
        ServiceHealth('webbie.service', 'Webbie resident assistant', 'running',
                      'Service is active'),
        ServiceHealth('spider-ai-dj.service', 'Nova / Spider AI DJ', 'stopped',
                      'Service is not active')]
    with patch('workspace_recovery.probe_user_services', return_value=sample_services):
        window.toggle_workspace_recovery()
        assert window.workspace_recovery.isVisible()
        worker = window.workspace_recovery.service_worker
        assert worker is not None and worker.wait(7000)
        app.processEvents()
        assert window.workspace_recovery.service_health.count() == 2
    window.workspace_recovery.refresh()
    assert window.workspace_recovery.list.count() == len(main.WORKSPACES) - 1
    assert not window.webbie_assistant.entry.text()
    window.workspace_recovery.prepare_webbie_status()
    assert 'webbie.service: running' in window.webbie_assistant.entry.text()
    assert 'spider-ai-dj.service: stopped' in window.webbie_assistant.entry.text()
    assert not window.webbie_assistant.pending
    window.workspace_recovery.copy_safe_diagnostics()
    import json
    diagnostic = json.loads(QApplication.clipboard().text())
    assert diagnostic['schema'] == 'spider-web-safe-diagnostics-v1'
    assert diagnostic['active_workspace'] == 'author'
    assert 'document_contents' not in diagnostic
    assert 'window_titles' not in diagnostic
    window.workspace_recovery.hide()
    assert window.close()
    reopened=main.TheWeb();assert reopened.tabs.count()==15;assert reopened.current_workspace=='author'
    assert reopened.tabs.indexOf(reopened.workspace_widgets['default']) == 0
    assert reopened.tabs.indexOf(reopened.workspace_widgets['study']) == 1
    assert reopened.appearance=='light'
    assert reopened.background_surface.appearance=='light'
    assert reopened.taskbar.styleSheet()==reopened.styleSheet()
    assert reopened.workspace_widgets['author'].native.store.chapter(chapter)['content']=='Edited inside the workspace tab'
    assert reopened.wallpaper_catalog.selected_id('deep-forage')==wallpaper_id
    app.processEvents()
    for active in (reopened.app_scan_worker, reopened.taskbar.window_scan_worker):
        if active is not None and active.isRunning():
            assert active.wait(10000)
    app.processEvents()
    assert reopened.close();app.processEvents()
    stored = main.read_desktop_state(window.state_path, main.WORKSPACES)
    # A minimal safe-start cannot overwrite the saved normal session.
    safe = main.TheWeb(restore=True, safe_mode=True)
    safe.show()
    assert safe.tabs.count() == 1
    assert safe.current_workspace == 'default'
    assert safe.safe_mode
    app.processEvents()
    for active in (safe.app_scan_worker, safe.taskbar.window_scan_worker):
        if active is not None and active.isRunning():
            assert active.wait(10000)
    app.processEvents()
    assert safe.close()
    assert main.read_desktop_state(window.state_path, main.WORKSPACES) == stored
    # Real desktop sessions reopen saved tabs in UI-event turns rather than
    # constructing every heavyweight native workspace in the constructor.
    import time
    main.write_desktop_state(window.state_path, {
        'open': ['default', 'studio', 'author', 'study'], 'active': 'study'},
        main.WORKSPACES)
    staged = main.TheWeb(desktop_mode=True)
    assert staged.tabs.count() == 1
    assert staged.is_staged_restoring()
    staged.show()
    began = time.monotonic()
    while staged.is_staged_restoring() and time.monotonic() - began < 20:
        app.processEvents()
        time.sleep(.025)
    assert not staged.is_staged_restoring()
    assert staged.tabs.count() == 4
    assert staged.current_workspace == 'study'
    assert set(staged.workspace_load_seconds) >= {'studio', 'author', 'study'}
    assert len(staged.workspace_load_seconds) == 3
    app.processEvents()
    for active in (staged.app_scan_worker, staged.taskbar.window_scan_worker):
        if active is not None and active.isRunning():
            assert active.wait(10000)
    app.processEvents()
    assert staged.close()
    # Safe-start can explicitly resume the previous session on the owner's
    # command, but never auto-opens the workspaces during initialization.
    safe_again = main.TheWeb(restore=True, safe_mode=True)
    assert safe_again.tabs.count() == 1
    assert safe_again.restore_last_saved_session()
    began = time.monotonic()
    while safe_again.is_staged_restoring() and time.monotonic() - began < 20:
        app.processEvents()
        time.sleep(.025)
    assert safe_again.tabs.count() == 4
    assert safe_again.current_workspace == 'study'
    assert not safe_again.safe_mode
    app.processEvents()
    for active in (safe_again.app_scan_worker, safe_again.taskbar.window_scan_worker):
        if active is not None and active.isRunning():
            assert active.wait(10000)
    app.processEvents()
    assert safe_again.close()
    app.processEvents()
    # Pause, prioritize and skip a queued native workspace. The saved normal
    # layout must remain untouched when any workspace was intentionally skipped.
    default_layout = {
        'open': ['default', 'studio', 'author', 'study'], 'active': 'study'}
    main.write_desktop_state(window.state_path, default_layout, main.WORKSPACES)
    guarded = main.TheWeb(desktop_mode=True)
    assert guarded.pause_staged_restore()
    app.processEvents()
    assert guarded.tabs.count() == 1
    assert guarded.staged_restore_status()['paused']
    guarded.toggle_workspace_recovery()
    recovery = guarded.workspace_recovery
    assert recovery.pause_restore.text() == 'Resume restoring'
    assert not recovery.adopt_layout.isEnabled()
    recovery.hide()
    assert guarded.prioritize_staged_workspace('study')
    assert guarded.skip_staged_workspace('author')
    assert guarded.staged_restore_status()['next'] == 'study'
    assert guarded.resume_staged_restore()
    started = time.monotonic()
    while guarded.is_staged_restoring() and time.monotonic() - started < 20:
        app.processEvents()
        time.sleep(.025)
    assert not guarded.is_staged_restoring()
    assert 'author' not in guarded.workspace_widgets
    assert 'study' in guarded.workspace_widgets
    assert 'studio' in guarded.workspace_widgets
    assert guarded._preserve_saved_session
    assert main.read_desktop_state(window.state_path, main.WORKSPACES)['open'] == default_layout['open']
    app.processEvents()
    for active in (guarded.app_scan_worker, guarded.taskbar.window_scan_worker):
        if active is not None and active.isRunning():
            assert active.wait(10000)
    app.processEvents()
    assert guarded.close()
    assert main.read_desktop_state(window.state_path, main.WORKSPACES)['open'] == default_layout['open']
    # Only the explicit adopt control replaces the old session on disk.
    interrupted = main.TheWeb(desktop_mode=True)
    assert interrupted.stop_staged_restore()
    app.processEvents()
    assert interrupted.tabs.count() == 1
    assert main.read_desktop_state(window.state_path, main.WORKSPACES)['open'] == default_layout['open']
    with patch.object(main, 'write_desktop_state', side_effect=OSError('read-only config')):
        assert not interrupted.adopt_current_layout()
    assert interrupted._preserve_saved_session
    assert main.read_desktop_state(window.state_path, main.WORKSPACES)['open'] == default_layout['open']
    assert interrupted.adopt_current_layout()
    assert main.read_desktop_state(window.state_path, main.WORKSPACES)['open'] == ['default']
    app.processEvents()
    for active in (interrupted.app_scan_worker, interrupted.taskbar.window_scan_worker):
        if active is not None and active.isRunning():
            assert active.wait(10000)
    app.processEvents()
    assert interrupted.close()
    app.processEvents()
print('DESKTOP INTEGRATION PASSED: 15 tabs, staged workspace startup, safe resume, seven native workspaces, saved editing/state/wallpapers, installed-app launching and safe close')
