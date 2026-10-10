"""Window confinement catches unselected windows and out-of-bounds clicks."""
import sys
from pathlib import Path
import unittest
from unittest.mock import Mock
from types import SimpleNamespace
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'webbie/actions'))
from window_safety import ConfinedDesktopOperator, parse_geometry


class WindowSafetyTests(unittest.TestCase):
    def test_geometry(self):
        self.assertEqual(parse_geometry('X=12\nY=33\nWIDTH=800\nHEIGHT=600\n'),(800,600))
        with self.assertRaises(RuntimeError):
            parse_geometry('WIDTH=-1\nHEIGHT=2\n')

    def test_rejects_unselected_actions(self):
        run=Mock()
        op=ConfinedDesktopOperator(permission=lambda a,p:True,runner=run,display=':0')
        with self.assertRaises(PermissionError):
            op.click(10,10)
        with self.assertRaises(PermissionError):
            op.type_text('hello')
        with self.assertRaises(PermissionError):
            op.press('Tab')
        run.assert_not_called()

    def test_targeted_window_and_bounds(self):
        target='0x03200009'
        foreground=str(int(target,16))
        def runner(argv, **kwargs):
            if argv[:2] == ['wmctrl','-lp']:
                return SimpleNamespace(stdout=target+' 0 42 host Audacity\n')
            if argv[:2] == ['xdotool','getactivewindow']:
                return SimpleNamespace(stdout=foreground+'\n')
            if argv[:2] == ['xdotool','getwindowgeometry']:
                return SimpleNamespace(stdout='WIDTH=400\nHEIGHT=300\n')
            return SimpleNamespace(stdout='')
        calls=[]
        def recording(argv, **kwargs):
            calls.append(argv)
            return runner(argv,**kwargs)
        op=ConfinedDesktopOperator(permission=lambda a,p:True,runner=recording,display=':0')
        op.bind_window(target)
        with self.assertRaises(PermissionError):
            op.focus('0x1')
        with self.assertRaises(ValueError):
            op.click(500,25)
        self.assertFalse(any(a[:2]==['xdotool','click'] for a in calls))
        self.assertEqual(op.click(100,25)['clicked_relative_to_window'],[100,25,1])
        self.assertTrue(any(a[:2]==['xdotool','click'] for a in calls))
        op.stop()
        with self.assertRaises(PermissionError):
            op.press('Tab')

    def test_focus_failure_blocks_mutation(self):
        def runner(argv, **kwargs):
            if argv[:2]==['wmctrl','-lp']:
                return SimpleNamespace(stdout='0x10 0 42 host Audacity\n')
            if argv[:2]==['xdotool','getactivewindow']:
                return SimpleNamespace(stdout='99999')
            return SimpleNamespace(stdout='')
        run=Mock(side_effect=runner)
        op=ConfinedDesktopOperator(permission=lambda a,p:True,runner=run,display=':0')
        op.bind_window('0x10')
        with self.assertRaises(RuntimeError):
            op.press('Tab')
        self.assertFalse(any(c.args[0][:2]==['xdotool','key'] for c in run.call_args_list))


if __name__=='__main__':
    unittest.main()
