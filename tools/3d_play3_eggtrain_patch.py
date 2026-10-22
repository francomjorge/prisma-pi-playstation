#!/usr/bin/env python3
from pathlib import Path
import sys
p=Path(sys.argv[1]); s=p.read_text()

def rep(old,new,label):
    global s
    if old not in s:
        raise SystemExit(f'3d_play3_eggtrain_patch: {label} pattern not found')
    s=s.replace(old,new,1)

rep(
    'use psx_gpu::prim::LineMono;\nmod mesh3d;\nuse mesh3d::{UFO_VERTS, UFO_FACES, UFO_UVS, ZURG_VERTS, ZURG_FACES, ZURG_UVS};',
    'use psx_gpu::prim::{LineMono, TriFlat};\nmod mesh3d;\nmod eggtrain;\nuse mesh3d::{UFO_VERTS, UFO_FACES, UFO_UVS, ZURG_VERTS, ZURG_FACES, ZURG_UVS};\nuse eggtrain::{EGGTRAIN_VERTS, EGGTRAIN_TRIS};',
    'imports')

# Character should start under manual control, not spinning automatically.
rep('let mut gte_auto: bool = true;', 'let mut gte_auto: bool = false;', 'auto rotate default')

# SELECT becomes a useful room reset instead of switching to the removed UFO.
rep(
    'if just_pressed(pressed, button::SELECT) { gte_model ^= 1; }',
    '''if just_pressed(pressed, button::SELECT) {
                        gte_x = 0;
                        gte_y = 0;
                        gte_z = 0x3600;
                        gte_vx = 0;
                        gte_vy = 0;
                        gte_vz = 0;
                    }''',
    'select reset')

# Constrain the existing inertial movement to the extracted Egg Train room.
rep(
'''                    if gte_x < -18000 { gte_x = -18000; gte_vx = 0; }
                    if gte_x >  18000 { gte_x =  18000; gte_vx = 0; }
                    if gte_y <  -6200 { gte_y =  -6200; gte_vy = 0; }
                    if gte_y >   6200 { gte_y =   6200; gte_vy = 0; }
                    if gte_z <   0x1800 { gte_z = 0x1800; gte_vz = 0; }
                    if gte_z >   0xB000 { gte_z = 0xB000; gte_vz = 0; }''',
'''                    if gte_x < -3600 { gte_x = -3600; gte_vx = 0; }
                    if gte_x >  3600 { gte_x =  3600; gte_vx = 0; }
                    if gte_y < -2200 { gte_y = -2200; gte_vy = 0; }
                    if gte_y >   300 { gte_y =   300; gte_vy = 0; }
                    if gte_z < 12400 { gte_z = 12400; gte_vz = 0; }
                    if gte_z > 15300 { gte_z = 15300; gte_vz = 0; }''',
    'room bounds')

# Replace the synthetic runway with the real Egg Train cutscene geometry.
start=s.find('fn render_play12_floor(gpu: &mut Gpu, cam_x: i32, cam_z: i32) {')
end=s.find('fn render_play11_mesh(',start)
if start<0 or end<0:
    raise SystemExit('3d_play3_eggtrain_patch: play12 floor block not found')
new_scene=r'''const EGGTRAIN_MAX_VERTS: usize = 1273;
const EGGTRAIN_MAX_TRIS: usize = 1926;

fn render_eggtrain_scene(gpu: &mut Gpu, cam_x: i32, cam_z: i32) {
    scene::set_screen_offset(160 << 16, 112 << 16);
    scene::set_projection_plane(220);
    scene::load_rotation(&Mat3I16::rotate_y(0));
    scene::load_translation(Vec3I32::new(-cam_x, 0, -cam_z));

    let mut projected = [scene::Projected::default(); EGGTRAIN_MAX_VERTS];
    let mut vi = 0usize;
    while vi < EGGTRAIN_VERTS.len() {
        projected[vi] = scene::project_vertex(EGGTRAIN_VERTS[vi]);
        vi += 1;
    }

    // Painter ordering with fixed storage: no heap and no new VRAM allocation.
    let mut head = [-1i16; 256];
    let mut next = [-1i16; EGGTRAIN_MAX_TRIS];
    let mut ti = 0usize;
    while ti < EGGTRAIN_TRIS.len() {
        let t = EGGTRAIN_TRIS[ti];
        let pa = projected[t.idx.0 as usize];
        let pb = projected[t.idx.1 as usize];
        let pc = projected[t.idx.2 as usize];
        let avg = ((pa.sz as u32 + pb.sz as u32 + pc.sz as u32) / 3) as u16;
        let mut bucket = (avg >> 6) as usize;
        if bucket > 255 { bucket = 255; }
        next[ti] = head[bucket];
        head[bucket] = ti as i16;
        ti += 1;
    }

    let mut bucket = 255i16;
    while bucket >= 0 {
        let mut cur = head[bucket as usize];
        while cur >= 0 {
            let i = cur as usize;
            let t = EGGTRAIN_TRIS[i];
            let pa = projected[t.idx.0 as usize];
            let pb = projected[t.idx.1 as usize];
            let pc = projected[t.idx.2 as usize];
            if pa.sz > 64 && pb.sz > 64 && pc.sz > 64 &&
               pa.sx > -1000 && pa.sx < 1000 && pa.sy > -800 && pa.sy < 800 &&
               pb.sx > -1000 && pb.sx < 1000 && pb.sy > -800 && pb.sy < 800 &&
               pc.sx > -1000 && pc.sx < 1000 && pc.sy > -800 && pc.sy < 800 {
                // First validation pass: industrial flat shading isolates geometry,
                // scale, depth and performance before spending another texture page.
                let near = ((255 - bucket as u8) >> 2).min(46);
                let base = 42u8.saturating_add(near);
                let (r,g,b) = match i % 5 {
                    0 => (base, base.saturating_add(8), base.saturating_add(18)),
                    1 => (base.saturating_add(10), base.saturating_add(6), base),
                    2 => (base / 2, base.saturating_add(28), base.saturating_add(18)),
                    3 => (base.saturating_add(16), base.saturating_add(16), base.saturating_add(20)),
                    _ => (base, base, base.saturating_add(10)),
                };
                gpu.draw(&TriFlat::new(
                    [(pa.sx,pa.sy),(pb.sx,pb.sy),(pc.sx,pc.sy)], r, g, b));
            }
            cur = next[i];
        }
        bucket -= 1;
    }
}

'''
s=s[:start]+new_scene+s[end:]

rep(
'''    render_play12_floor(gpu, cam_x, cam_z);

    let view_x = world_x - cam_x;
    let view_z = world_z - cam_z;

    if model == 0 {
        render_play11_mesh(
            gpu, &UFO_VERTS, &UFO_FACES, &UFO_UVS,
            PLAY11_UFO_TPAGE, PLAY11_UFO_CLUT,
            frame, yaw, view_x, world_y, view_z,
        );
    } else {
        render_play11_mesh(
            gpu, &ZURG_VERTS, &ZURG_FACES, &ZURG_UVS,
            PLAY11_ZURG_TPAGE, PLAY11_ZURG_CLUT,
            frame, yaw, view_x, world_y, view_z,
        );
    }''',
'''    render_eggtrain_scene(gpu, cam_x, cam_z);

    let view_x = world_x - cam_x;
    let view_z = world_z - cam_z;
    render_play11_mesh(
        gpu, &ZURG_VERTS, &ZURG_FACES, &ZURG_UVS,
        PLAY11_ZURG_TPAGE, PLAY11_ZURG_CLUT,
        frame, yaw, view_x, 3000 + world_y, view_z,
    );''',
    'scene and player')

rep('font.draw_text(8, 6, "3D PLAY 1.2 / FLIGHT", (0x70, 0xD0, 0xD0));',
    'font.draw_text(8, 6, "3D PLAY 3 / EGG TRAIN", (0x70, 0xD0, 0xD0));',
    'title')
rep('font.draw_text(8, 22, "ALIEN MOTHERSHIP / 753 TRI", (0x58, 0x90, 0x90));',
    'font.draw_text(8, 22, "ZURG / EGG TRAIN 1926 TRI", (0x58, 0x90, 0x90));',
    'ufo label')
rep('font.draw_text(8, 22, "FLOATING ZURG / 891 TRI", (0x90, 0x58, 0x80));',
    'font.draw_text(8, 22, "ZURG / EGG TRAIN 1926 TRI", (0x90, 0x58, 0x80));',
    'zurg label')
rep('font.draw_text(8, 174, "D-PAD = THRUST    TRI/X = LIFT", (0x68, 0x68, 0x70));',
    'font.draw_text(8, 174, "D-PAD = MOVE    TRI/X = HEIGHT", (0x68, 0x68, 0x70));',
    'controls label')
rep('font.draw_text(8, 190, "INERTIA + FOLLOW CAM   SQUARE = RATE", (0x68, 0x68, 0x70));',
    'font.draw_text(8, 190, "L1/R1=TURN  SQUARE=RATE  SELECT=RESET", (0x68, 0x68, 0x70));',
    'hud2')
rep('font.draw_text(8, 206, "SELECT = MODEL", (0x68, 0x68, 0x70));',
    'font.draw_text(8, 206, "PLAYER = ZURG / FOLLOW CAM", (0x68, 0x68, 0x70));',
    'select hud')

p.write_text(s)
print('3d_play3_eggtrain_patch: installed flat Egg Train room + textured Zurg player')
