#!/usr/bin/env python3
from pathlib import Path
import sys
p=Path(sys.argv[1]); s=p.read_text()
def rep(old,new,label):
    global s
    if old not in s: raise SystemExit(f'3d_play13b: {label} pattern not found')
    s=s.replace(old,new,1)

rep(
'use extra_chars::{TYRANT_VERTS, TYRANT_FACES, TREX_VERTS, TREX_FACES};',
'use extra_chars::{TYRANT_VERTS, TYRANT_FACES, TREX_VERTS, TREX_FACES};\nmod extra_uvs;\nuse extra_uvs::{TYRANT_UVS, TREX_UVS};',
'uv imports')

rep(
'const PLAY11_ZURG_CLUT: Clut = Clut::new(512, 497);',
'''const PLAY11_ZURG_CLUT: Clut = Clut::new(512, 497);\nstatic PLAY13B_TYRANT_TEX: &[u8] = include_bytes!("play13b_tyrant_tex.bin");\nstatic PLAY13B_TREX_TEX: &[u8] = include_bytes!("play13b_trex_tex.bin");''',
'texture statics')

rep(
'''    let mut gte_cam_x: i32 = 0;\n    let mut gte_cam_z: i32 = 0;''',
'''    let mut gte_cam_x: i32 = 0;\n    let mut gte_cam_z: i32 = 0;\n    let mut gte_scale_q12: i32 = 4096;''',
'scale state')

rep(
'if just_pressed(pressed, button::SELECT) { gte_model = if gte_model >= 3 { 0 } else { gte_model + 1 }; }',
'''if just_pressed(pressed, button::SELECT) {\n                        gte_model = if gte_model >= 3 { 0 } else { gte_model + 1 };\n                        upload_play13b_model_texture(gte_model);\n                    }\n                    if just_pressed(pressed, button::L2) { gte_scale_q12 = 4096; }''',
'select + reset')

rep(
'''                    let turn = (gte_rate as u16) * 10;\n                    if held(bits, button::L1) { gte_yaw = gte_yaw.wrapping_sub(turn); }\n                    if held(bits, button::R1) { gte_yaw = gte_yaw.wrapping_add(turn); }''',
'''                    let turn = (gte_rate as u16) * 10;\n                    if held(bits, button::R2) {\n                        let ss = match gte_rate { 1=>32i32, 2=>48i32, 3=>72i32, 4=>104i32, _=>144i32 };\n                        if held(bits, button::L1) { gte_scale_q12 = (gte_scale_q12 - ss).max(1024); }\n                        if held(bits, button::R1) { gte_scale_q12 = (gte_scale_q12 + ss).min(12288); }\n                    } else {\n                        if held(bits, button::L1) { gte_yaw = gte_yaw.wrapping_sub(turn); }\n                        if held(bits, button::R1) { gte_yaw = gte_yaw.wrapping_add(turn); }\n                    }''',
'scale controls')

rep(
'''            Screen::GteTest => render_gte_test(&font, &mut gpu, gte_frame, gte_model, gte_yaw, gte_auto, gte_rate, gte_x, gte_y, gte_z, gte_cam_x, gte_cam_z),''',
'''            Screen::GteTest => render_gte_test(&font, &mut gpu, gte_frame, gte_model, gte_yaw, gte_auto, gte_rate, gte_x, gte_y, gte_z, gte_cam_x, gte_cam_z, gte_scale_q12),''',
'render call')

rep(
'''    world_z: i32,\n) {\n    scene::set_screen_offset(160 << 16, 112 << 16);''',
'''    world_z: i32,\n    scale_q12: i32,\n) {\n    scene::set_screen_offset(160 << 16, 112 << 16);''',
'play11 signature')

rep(
'''    scene::load_rotation(&yaw.mul(&pitch));''',
'''    let scaled = yaw.mul(&pitch).scale_columns_q12([scale_q12, scale_q12, scale_q12]);\n    scene::load_rotation(&scaled);''',
'play11 scale')

insert=s.find('fn render_gte_test(\n')
if insert<0: raise SystemExit('3d_play13b: render_gte_test not found')
helper=r'''fn upload_play13b_compact(data: &[u8]) {\n    const PX: usize = 64*64;\n    let r=VramRect::new(PLAY11_UFO_TPAGE.x(), PLAY11_UFO_TPAGE.y(), 32, 64);\n    upload_bytes(r, &data[..PX]);\n    let c=VramRect::new(PLAY11_UFO_CLUT.x(), PLAY11_UFO_CLUT.y(), 256, 1);\n    upload_bytes(c, &data[PX..]);\n}\n\nfn restore_play11_ufo_texture() {\n    let r=VramRect::new(PLAY11_UFO_TPAGE.x(), PLAY11_UFO_TPAGE.y(), 128, 256);\n    upload_bytes(r, &PLAY11_UFO_TEX[..PLAY11_TEX_PIXELS]);\n    let c=VramRect::new(PLAY11_UFO_CLUT.x(), PLAY11_UFO_CLUT.y(), 256, 1);\n    upload_bytes(c, &PLAY11_UFO_TEX[PLAY11_TEX_PIXELS..]);\n}\n\nfn upload_play13b_model_texture(model:u8) {\n    match model {\n        0 => restore_play11_ufo_texture(),\n        2 => upload_play13b_compact(PLAY13B_TYRANT_TEX),\n        3 => upload_play13b_compact(PLAY13B_TREX_TEX),\n        _ => {}\n    }\n}\n\nconst PLAY13B_MAX_VERTS: usize = 917;\nconst PLAY13B_MAX_FACES: usize = 1718;\nfn render_play13b_extra_textured(\n    verts:&[Vec3I16], faces:&[(u16,u16,u16)], face_uvs:&[[(u8,u8);3]],\n    frame:u16, yaw_manual:u16, world_x:i32, world_y:i32, world_z:i32, scale_q12:i32,\n) {\n    scene::set_screen_offset(160 << 16, 112 << 16);\n    scene::set_projection_plane(220);\n    scene::load_translation(Vec3I32::new(world_x, world_y, world_z));\n    let yaw=Mat3I16::rotate_y(yaw_manual.wrapping_add(frame.wrapping_mul(4)));\n    let pitch=Mat3I16::rotate_x(96);\n    let scaled=yaw.mul(&pitch).scale_columns_q12([scale_q12,scale_q12,scale_q12]);\n    scene::load_rotation(&scaled);\n\n    let mut projected=[scene::Projected::default(); PLAY13B_MAX_VERTS];\n    let mut vi=0usize;\n    while vi<verts.len(){ projected[vi]=scene::project_vertex(verts[vi]); vi+=1; }\n\n    let mut head=[-1i16;256];\n    let mut next=[-1i16;PLAY13B_MAX_FACES];\n    let mut fi=0usize;\n    while fi<faces.len(){\n        let(a,b,c)=faces[fi];\n        let pa=projected[a as usize]; let pb=projected[b as usize]; let pc=projected[c as usize];\n        let avg=((pa.sz as u32+pb.sz as u32+pc.sz as u32)/3) as u16;\n        let mut bucket=(avg>>6) as usize; if bucket>255{bucket=255;}\n        next[fi]=head[bucket]; head[bucket]=fi as i16; fi+=1;\n    }\n    let mut bucket=255i16;\n    while bucket>=0 {\n        let mut cur=head[bucket as usize];\n        while cur>=0 {\n            let i=cur as usize; let(a,b,c)=faces[i];\n            let pa=projected[a as usize]; let pb=projected[b as usize]; let pc=projected[c as usize];\n            if pa.sz>64 && pb.sz>64 && pc.sz>64 &&\n               pa.sx>-900 && pa.sx<900 && pa.sy>-700 && pa.sy<700 &&\n               pb.sx>-900 && pb.sx<900 && pb.sy>-700 && pb.sy<700 &&\n               pc.sx>-900 && pc.sx<900 && pc.sy>-700 && pc.sy<700 {\n                draw_play11_textured_tri([(pa.sx,pa.sy),(pb.sx,pb.sy),(pc.sx,pc.sy)], face_uvs[i], PLAY11_UFO_TPAGE, PLAY11_UFO_CLUT);\n            }\n            cur=next[i];\n        }\n        bucket-=1;\n    }\n}\n\n'''.replace('\\n','\n')
s=s[:insert]+helper+s[insert:]

rep(
'''    cam_x: i32,\n    cam_z: i32,\n) {''',
'''    cam_x: i32,\n    cam_z: i32,\n    scale_q12: i32,\n) {''',
'render signature')

rep(
'''            frame, yaw, view_x, world_y, view_z,\n        );''',
'''            frame, yaw, view_x, world_y, view_z, scale_q12,\n        );''',
'ufo scale arg')
rep(
'''            frame, yaw, view_x, world_y, view_z,\n        );''',
'''            frame, yaw, view_x, world_y, view_z, scale_q12,\n        );''',
'zurg scale arg')

rep(
'''    } else if model == 2 {\n        render_play12_extra_flat(gpu,&TYRANT_VERTS,&TYRANT_FACES,frame,yaw,view_x,world_y,view_z,model);\n    } else {\n        render_play12_extra_flat(gpu,&TREX_VERTS,&TREX_FACES,frame,yaw,view_x,world_y,view_z,model);\n    }''',
'''    } else if model == 2 {\n        render_play13b_extra_textured(&TYRANT_VERTS,&TYRANT_FACES,&TYRANT_UVS,frame,yaw,view_x,world_y,view_z,scale_q12);\n    } else {\n        render_play13b_extra_textured(&TREX_VERTS,&TREX_FACES,&TREX_UVS,frame,yaw,view_x,world_y,view_z,scale_q12);\n    }''',
'extra renderer')

rep(
'font.draw_text(8, 190, "INERTIA + FOLLOW CAM   SQUARE = RATE", (0x68, 0x68, 0x70));',
'font.draw_text(8, 190, "R2+L1/R1 = SCALE   L2 = RESET", (0x68, 0x68, 0x70));',
'hud scale')

p.write_text(s)\nprint('3d_play13b: safe textures on recovery renderer + scale')
