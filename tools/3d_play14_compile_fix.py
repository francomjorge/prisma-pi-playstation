#!/usr/bin/env python3
from pathlib import Path
import sys
p=Path(sys.argv[1]); s=p.read_text()
old='const PLAY14_BOARD_HALF: i32 = 12000;'
new='const PLAY14_MAX_VERTS: usize = 917;\nconst PLAY14_MAX_FACES: usize = 1718;\nconst PLAY14_BOARD_HALF: i32 = 12000;'
if old not in s: raise SystemExit('play14 compile fix: board const anchor not found')
s=s.replace(old,new,1)
s=s.replace('PLAY13B_MAX_VERTS','PLAY14_MAX_VERTS')
s=s.replace('PLAY13B_MAX_FACES','PLAY14_MAX_FACES')
p.write_text(s)
print('3d_play14_compile_fix: local max mesh constants installed')
