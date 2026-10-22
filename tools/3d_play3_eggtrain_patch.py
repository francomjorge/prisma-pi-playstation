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
    'mod mesh3d;\nuse mesh3d::{UFO_VERTS, UFO_FACES, UFO_UVS, ZURG_VERTS, ZURG_FACES, ZURG_UVS};',
    'mod mesh3d;\nmod eggtrain;\nuse mesh3d::{UFO_VERTS, UFO_FACES, UFO_UVS, ZURG_VERTS, ZURG_FACES, ZURG_UVS};\nuse eggtrain::{EGGTRAIN_VERTS, EGGTRAIN_TRIS};',
    'imports')

rep(
    'const PLAY11_ZURG_CLUT: Clut = Clut::new(512, 497);',
    '''const PLAY11_ZURG_CLUT: Clut = Clut::new(512, 497);

// 3D PLAY 3: Egg Train interior. One compact 256x256 8-bit atlas + CLUT.
// This deliberately reuses the old UFO page; Zurg remains textured on its original page.
static EGGTRAIN_TEX: &[u8] = include_bytes!("eggtrain_atlas.bin");
const EGGTRAIN_TEX_PIXELS: usize = 256 * 256;
const EGGTRAIN_TPAGE: TexturePage = TexturePage::new(768, 0, TextureDepth::Bit8);
const EGGTRAIN_CLUT: Clut = Clut::new(256, 497);''',
    'constants')

rep(
    '    upload_prisma_image();\n    upload_play11_textures();',
    '    upload_prisma_image();\n    upload_play11_textures();\n    upload_eggtrain_texture();',
    'texture upload')

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

start=s.find('fn render_play12_floor(gpu: &mut Gpu, cam_x: i32, cam_z: i32) {')
end=s.find('fn render_play11_mesh(',start)
if start<0 or end<0:
    raise SystemExit('3d_play3_eggtrain_patch: play12 floor block not found')
new_scene=r'''const EGGTRAIN_MAX_VERTS: usize = 1273;
const EGGTRAIN_MAX_TRIS: usize = 1926;

fn upload_eggtrain_texture() {
    let r = VramRect::new(EGGTRAIN_TPAGE.x(), EGGTRAIN_TPAGE.y(), 128, 256);
    upload_bytes(r, &EGGTRAIN_TEX[..EGGTRAIN_TEX_PIXELS]);
    let c = VramRect::new(EGGTRAIN_CLUT.x(), EGGTRAIN_CLUT.y(), 256, 1);
    upload_bytes(c, &EGGTRAIN_TEX[EGGTRAIN_TEX_PIXELS..]);
}

fn render_eggtrain_scene(cam_x: i32, cam_z: i32) {
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
                draw_play11_textured_tri(
                    [(pa.sx,pa.sy),(pb.sx,pb.sy),(pc.sx,pc.sy)],
                    t.uv, EGGTRAIN_TPAGE, EGGTRAIN_CLUT);
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
'''    render_eggtrain_scene(cam_x, cam_z);

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
    'font.draw_text(8, 22, "ZURG IN EGG TRAIN / 1926 ENV TRI", (0x58, 0x90, 0x90));',
    'ufo label')
rep('font.draw_text(8, 22, "FLOATING ZURG / 891 TRI", (0x90, 0x58, 0x80));',
    'font.draw_text(8, 22, "ZURG IN EGG TRAIN / 1926 ENV TRI", (0x90, 0x58, 0x80));',
    'zurg label')
rep('font.draw_text(8, 174, "D-PAD = THRUST    TRI/X = LIFT", (0x68, 0x68, 0x70));',
    'font.draw_text(8, 174, "D-PAD = MOVE    TRI/X = HEIGHT", (0x68, 0x68, 0x70));',
    'controls label')
rep('font.draw_text(8, 190, "INERTIA + FOLLOW CAM   SQUARE = RATE", (0x68, 0x68, 0x70));',
    'font.draw_text(8, 190, "EGG TRAIN ROOM + FOLLOW CAM", (0x68, 0x68, 0x70));',
    'hud2')
rep('font.draw_text(8, 206, "SELECT = MODEL", (0x68, 0x68, 0x70));',
    'font.draw_text(8, 206, "PLAYER = ZURG", (0x68, 0x68, 0x70));',
    'select hud')

p.write_text(s)
print('3d_play3_eggtrain_patch: installed Egg Train room + Zurg player')
