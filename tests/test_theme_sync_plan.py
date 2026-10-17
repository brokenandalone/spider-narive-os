"""Dry-run KDE/GTK theme coordination: never rewrite owner's native themes."""
import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'the-web/shell'))
from PyQt5.QtWidgets import QApplication
import theme_sync_plan as sync
import quick_settings as quick

APP=QApplication.instance() or QApplication([])


class ThemeSyncPlanningTests(unittest.TestCase):
    def _roots(self, root):
        path=Path(root)/'share/color-schemes'
        path.mkdir(parents=True,exist_ok=True)
        (path/'BreezeDark.colors').write_text('[General]\nName=Breeze Dark\n')
        (path/'BreezeLight.colors').write_text('[General]\nName=Breeze Light\n')
        return (Path(root)/'share',)

    def test_preview_exact_breeze_options_and_no_writes(self):
        with tempfile.TemporaryDirectory() as tmp:
            roots=self._roots(tmp)
            before={p:p.read_bytes() for p in (roots[0]/'color-schemes').iterdir()}
            current={'KDE colors':'CustomPurple','GTK 3':'CustomGTK','GTK 4':'System'}
            plan=sync.plan_theme('dark',env={'XDG_CURRENT_DESKTOP':'TheWeb:KDE'},
                                 data_roots=roots,which=lambda name:'/usr/bin/plasma-apply-colorscheme',
                                 snapshot=lambda:current)
            self.assertTrue(plan['dry_run'])
            self.assertFalse(plan['mutates_files'])
            self.assertTrue(plan['requires_separate_approval'])
            self.assertEqual(plan['scheme'],'BreezeDark')
            self.assertTrue(plan['installed'])
            self.assertEqual(plan['existing'],current)
            self.assertEqual(plan['blockers'],[])
            self.assertIn('READ-ONLY',sync.render_plan(plan))
            self.assertIn('CustomPurple',sync.render_plan(plan))
            self.assertEqual(before,{p:p.read_bytes() for p in before})

    def test_missing_plasma_tool_and_scheme_are_explicit_blockers(self):
        with tempfile.TemporaryDirectory() as tmp:
            report=sync.plan_theme('light',env={'XDG_CURRENT_DESKTOP':'TheWeb'},
                                   data_roots=[Path(tmp)],which=lambda name:None,
                                   snapshot=lambda:{})
            self.assertFalse(report['installed'])
            self.assertFalse(report['plasma_tool_present'])
            self.assertTrue(any('BreezeLight' in msg for msg in report['blockers']))
            self.assertTrue(any('command' in msg for msg in report['blockers']))

    def test_gtk_theme_override_and_unknown_session_warn_not_mutate(self):
        with tempfile.TemporaryDirectory() as tmp:
            roots=self._roots(tmp)
            report=sync.plan_theme('dark',env={'GTK_THEME':'Custom:dark','XDG_CURRENT_DESKTOP':'i3'},
                                   data_roots=roots,
                                   which=lambda name:'/usr/bin/plasma-apply-colorscheme',
                                   snapshot=lambda:{})
            self.assertTrue(any('GTK_THEME' in msg for msg in report['blockers']))
            self.assertTrue(any('desktop' in msg for msg in report['blockers']))
            self.assertNotIn('Custom:dark',sync.render_plan(report))

    def test_malicious_theme_names_refused(self):
        for mode in ('../Dark', 'custom', '', None, 12, True, [], {}):
            with self.assertRaises(ValueError):
                sync.plan_theme(mode,env={},data_roots=(),snapshot=lambda:{})
        with tempfile.TemporaryDirectory() as tmp:
            roots=self._roots(tmp)
            self.assertFalse(sync.available_scheme('../Dark', roots))

    def test_preview_ui_never_invokes_theme_writer(self):
        with patch.object(quick,'plan_theme',return_value={'mode':'dark',
                         'scheme':'BreezeDark','desktop':'TheWeb:KDE','installed':True,
                         'plasma_tool_present':True,'existing':{},'blockers':[],
                         'steps':['No changes'], 'dry_run':True}) as plan, \
             patch.object(quick.QMessageBox,'information') as info:
            calls=[]
            panel=quick.QuickSettingsPanel(appearance_reader=lambda:'dark',
                                           appearance_writer=lambda value:calls.append(value))
            self.assertTrue(panel.worker.wait(4000))
            APP.processEvents()
            panel.theme_sync_preview.click()
            plan.assert_called_once_with('dark', portal=panel._portal_preference)
            info.assert_called_once()
            self.assertIn('READ-ONLY',info.call_args.args[2])
            self.assertEqual(calls,[])
            panel.close()

    def test_portal_mismatch_and_unknown_status_are_explained(self):
        for portal, fragment in [('Light preferred', 'differs'),
                                 ('No preference', 'own default'),
                                 ('Unavailable', 'could not be verified')]:
            report=sync.plan_theme('dark', env={'XDG_CURRENT_DESKTOP':'The-Web'},
                data_roots=(), which=lambda name:None, snapshot=lambda:{}, portal=portal)
            self.assertIn(fragment, ' '.join(report['notes']))
            self.assertIn(portal, sync.render_plan(report))
            self.assertFalse(any('desktop is not confirmed' in p for p in report['blockers']))
        report=sync.plan_theme('dark', env={'XDG_CURRENT_DESKTOP':'NOTKDE'},
            data_roots=(), which=lambda name:None, snapshot=lambda:{}, portal='Dark preferred')
        self.assertEqual(report['notes'], [])
        self.assertTrue(any('desktop is not confirmed' in p for p in report['blockers']))

    def test_relative_xdg_data_home_is_ignored(self):
        roots=sync.default_data_roots({'XDG_DATA_HOME':'relative', 'XDG_DATA_DIRS':'relative:/usr/share'})
        self.assertTrue(all(root.is_absolute() for root in roots))


if __name__=='__main__':
    unittest.main()
