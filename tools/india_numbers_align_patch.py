#!/usr/bin/env python3
import pathlib
import sys

path = pathlib.Path(sys.argv[1])
s = path.read_text()

old = '''    let num_x = panel_x + 78;\n    let num_y = panel_y + 18;\n'''
new = '''    // Fine alignment against the baked PS1 panel: one pixel left/down.\n    let num_x = panel_x + 77;\n    let num_y = panel_y + 19;\n'''

if old not in s:
    raise SystemExit('india number alignment patch failed: numeric origin not found')

s = s.replace(old, new, 1)
path.write_text(s)
print(f'Applied INDIA numeric alignment (-1 X, +1 Y) to {path}')
