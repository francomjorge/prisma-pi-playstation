#!/usr/bin/env python3
from pathlib import Path
import sys
p=Path(sys.argv[1]); s=p.read_text()
def rep(old,new,label):
    global s
    if old not in s: raise SystemExit(f'3d_play13_prep: {label} pattern not found')
    s=s.replace(old,new,1)
rep(
'if just_pressed(pressed, button::SELECT) { gte_model = if gte_model >= 3 { 0 } else { gte_model + 1 }; }',
'if just_pressed(pressed, button::SELECT) { gte_model = (gte_model + 1) & 3; }',
'select normalize')
rep(
'''    if model == 0 {
        render_play11_mesh(
            gpu, &UFO_VERTS, &UFO_FACES, &UFO_UVS,
            PLAY11_UFO_TPAGE, PLAY11_UFO_CLUT,
            frame, yaw, view_x, world_y, view_z,
        );
    } else if model == 1 {
        render_play11_mesh(
            gpu, &ZURG_VERTS, &ZURG_FACES, &ZURG_UVS,
            PLAY11_ZURG_TPAGE, PLAY11_ZURG_CLUT,
            frame, yaw, view_x, world_y, view_z,
        );
    } else if model == 2 {
        render_play12_extra_flat(gpu,&TYRANT_VERTS,&TYRANT_FACES,frame,yaw,view_x,world_y,view_z,model);
    } else {
        render_play12_extra_flat(gpu,&TREX_VERTS,&TREX_FACES,frame,yaw,view_x,world_y,view_z,model);
    }''',
'''    match model {
        0 => render_play11_mesh(
            gpu, &UFO_VERTS, &UFO_FACES, &UFO_UVS,
            PLAY11_UFO_TPAGE, PLAY11_UFO_CLUT,
            frame, yaw, view_x, world_y, view_z,
        ),
        1 => render_play11_mesh(
            gpu, &ZURG_VERTS, &ZURG_FACES, &ZURG_UVS,
            PLAY11_ZURG_TPAGE, PLAY11_ZURG_CLUT,
            frame, yaw, view_x, world_y, view_z,
        ),
        2 => render_extra_character(
            gpu, &TYRANT_VERTS, &TYRANT_FACES,
            frame, yaw, view_x, world_y, view_z, 0,
        ),
        _ => render_extra_character(
            gpu, &TREX_VERTS, &TREX_FACES,
            frame, yaw, view_x, world_y, view_z, 1,
        ),
    }''',
'render selector normalize')
rep(
'font.draw_text(8, 206, "SELECT = MODEL", (0x68, 0x68, 0x70));',
'font.draw_text(8, 206, "SELECT = NEXT MODEL", (0x68, 0x68, 0x70));',
'hud normalize')
p.write_text(s)
print('3d_play13_prep: recovery syntax normalized for 1.3 patch')
