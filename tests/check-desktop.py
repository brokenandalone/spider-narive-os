"""Run the desktop integration check from the source checkout."""
import runpy
from pathlib import Path
runpy.run_path(str(Path(__file__).with_name('check-the-web.py')), run_name='__main__')
