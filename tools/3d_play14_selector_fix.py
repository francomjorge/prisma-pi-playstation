#!/usr/bin/env python3
from pathlib import Path
import sys
p=Path(sys.argv[1]); s=p.read_text()
old='''                    if just_pressed(pressed, button::SELECT) {
                        gte_model = if gte_model >= 3 { 0 } else { gte_model + 1 };
                        upload_play13b_model_texture(gte_model);
                    }
                    if just_pressed(pressed, button::L2) { gte_scale_q12 = 4096; }'''
new='''                    // PLAY 1.4 renders all four models simultaneously; SELECT is handled below as POV recenter.
                    if just_pressed(pressed, button::L2) { gte_scale_q12 = 4096; }'''
if old not in s: raise SystemExit('play14 selector fix: inherited selector block not found')
s=s.replace(old,new,1)
p.write_text(s)
print('3d_play14_selector_fix: inherited single-model selector disabled')
