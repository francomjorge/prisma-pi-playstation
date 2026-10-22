#!/usr/bin/env python3
from pathlib import Path
import base64, gzip, struct, sys

main = Path(sys.argv[1])
outdir = main.parent

# Build UV module directly from the compact source asset.
raw = gzip.decompress(base64.b64decode(Path('assets/3d/play13_extra_uvs.b64').read_text().strip()))
o = 0
parts = ['// Auto-generated compact UVs for PLAY 1.3b\n\n']
for name in ('TYRANT','TREX'):
    fcount = struct.unpack_from('<H', raw, o)[0]; o += 2
    parts.append(f'pub const {name}_UVS: [[(u8,u8);3]; {fcount}] = [\n')
    for _ in range(fcount):
        v = struct.unpack_from('<BBBBBB', raw, o); o += 6
        parts.append(f'    [({v[0]>>2},{v[1]>>2}),({v[2]>>2},{v[3]>>2}),({v[4]>>2},{v[5]>>2})],\n')
    parts.append('];\n\n')
(outdir/'extra_uvs.rs').write_text(''.join(parts))

# Decode compact 64x64 8bpp texture payloads + 256-entry CLUTs.
for src, dst in [
    ('assets/3d/play13_tyrant_64.b64','play13b_tyrant_tex.bin'),
    ('assets/3d/play13_trex_64.b64','play13b_trex_tex.bin'),
]:
    data = gzip.decompress(base64.b64decode(Path(src).read_text().strip()))
    if len(data) != 64*64 + 512:
        raise SystemExit(f'3d_play13b: bad texture payload {src}: {len(data)}')
    (outdir/dst).write_bytes(data)

s = main.read_text()
def rep(old,new,label):
    global s
    if old not in s:
        raise SystemExit(f'3d_play13b: {label} pattern not found')
    s = s.replace(old,new,1)

rep(
    'use extra_chars::{TYRANT_VERTS, TYRANT_FACES, TREX_VERTS, TREX_FACES};',
    'use extra_chars::{TYRANT_VERTS, TYRANT_FACES, TREX_VERTS, TREX_FACES};\nmod extra_uvs;\nuse extra_uvs::{TYRANT_UVS, TREX_UVS};',
    'uv imports')

rep(
    'const PLAY11_ZURG_CLUT: Clut = Clut::new(512, 497);',
    '''const PLAY11_ZURG_CLUT: Clut = Clut::new(512, 497);
static PLAY13B_TYRANT_TEX: &[u8] = include_bytes!("play13b_tyrant_tex.bin");
static PLAY13B_TREX_TEX: &[u8] = include_bytes!("play13b_trex_tex.bin");''',
    'texture statics')

rep(
    '''    let mut gte_cam_x: i32 = 0;
    let mut gte_cam_z: i32 = 0;''',
    '''    let mut gte_cam_x: i32 = 0;
    let mut gte_cam_z: i32 = 0;
    let mut gte_scale_q12: i32 = 4096;''',
    'scale state')

rep(
    'if just_pressed(pressed, button::SELECT) { gte_model = if gte_model >= 3 { 0 } else { gte_model + 1 }; }',
    '''if just_pressed(pressed, button::SELECT) {
                        gte_model = if gte_model >= 3 { 0 } else { gte_model + 1 };
                        upload_play13b_model_texture(gte_model);
                    }
                    if just_pressed(pressed, button::L2) { gte_scale_q12 = 4096; }''',
    'select')

rep(
    '''                    let turn = (gte_rate as u16) * 10;
                    if held(bits, button::L1) { gte_yaw = gte_yaw.wrapping_sub(turn); }
                    if held(bits, button::R1) { gte_yaw = gte_yaw.wrapping_add(turn); }''',
    '''                    let turn = (gte_rate as u16) * 10;
                    if held(bits, button::R2) {
                        let ss = match gte_rate { 1=>32i32, 2=>48i32, 3=>72i32, 4=>104i32, _=>144i32 };
                        if held(bits, button::L1) { gte_scale_q12 = (gte_scale_q12 - ss).max(1024); }
                        if held(bits, button::R1) { gte_scale_q12 = (gte_scale_q12 + ss).min(12288); }
                    } else {
                        if held(bits, button::L1) { gte_yaw = gte_yaw.wrapping_sub(turn); }
                        if held(bits, button::R1) { gte_yaw = gte_yaw.wrapping_add(turn); }
                    }''',
    'scale controls')

rep(
    '            Screen::GteTest => render_gte_test(&font, &mut gpu, gte_frame, gte_model, gte_yaw, gte_auto, gte_rate, gte_x, gte_y, gte_z, gte_cam_x, gte_cam_z),',
    '            Screen::GteTest => render_gte_test(&font, &mut gpu, gte_frame, gte_model, gte_yaw, gte_auto, gte_rate, gte_x, gte_y, gte_z, gte_cam_x, gte_cam_z, gte_scale_q12),',
    'render call')

rep(
    '''    world_z: i32,
) {
    scene::set_screen_offset(160 << 16, 112 << 16);''',
    '''    world_z: i32,
    scale_q12: i32,
) {
    scene::set_screen_offset(160 << 16, 112 << 16);''',
    'play11 signature')

rep(
    '    scene::load_rotation(&yaw.mul(&pitch));',
    '''    let scaled = yaw.mul(&pitch).scale_columns_q12([scale_q12, scale_q12, scale_q12]);
    scene::load_rotation(&scaled);''',
    'play11 scale')

insert = s.find('fn render_gte_test(\n')
if insert < 0:
    raise SystemExit('3d_play13b: render_gte_test not found')
helper = r'''fn upload_play13b_compact(data: &[u8]) {
    const PX: usize = 64 * 64;
    let r = VramRect::new(PLAY11_UFO_TPAGE.x(), PLAY11_UFO_TPAGE.y(), 32, 64);
    upload_bytes(r, &data[..PX]);
    let c = VramRect::new(PLAY11_UFO_CLUT.x(), PLAY11_UFO_CLUT.y(), 256, 1);
    upload_bytes(c, &data[PX..]);
}

fn restore_play11_ufo_texture() {
    let r = VramRect::new(PLAY11_UFO_TPAGE.x(), PLAY11_UFO_TPAGE.y(), 128, 256);
    upload_bytes(r, &PLAY11_UFO_TEX[..PLAY11_TEX_PIXELS]);
    let c = VramRect::new(PLAY11_UFO_CLUT.x(), PLAY11_UFO_CLUT.y(), 256, 1);
    upload_bytes(c, &PLAY11_UFO_TEX[PLAY11_TEX_PIXELS..]);
}

fn upload_play13b_model_texture(model: u8) {
    match model {
        0 => restore_play11_ufo_texture(),
        2 => upload_play13b_compact(PLAY13B_TYRANT_TEX),
        3 => upload_play13b_compact(PLAY13B_TREX_TEX),
        _ => {}
    }
}

fn render_play13b_extra_textured(
    verts: &[Vec3I16],
    faces: &[(u16,u16,u16)],
    face_uvs: &[[(u8,u8);3]],
    frame: u16,
    yaw_manual: u16,
    world_x: i32,
    world_y: i32,
    world_z: i32,
    scale_q12: i32,
) {
    scene::set_screen_offset(160 << 16, 112 << 16);
    scene::set_projection_plane(220);
    scene::load_translation(Vec3I32::new(world_x, world_y, world_z));
    let yaw = Mat3I16::rotate_y(yaw_manual.wrapping_add(frame.wrapping_mul(4)));
    let pitch = Mat3I16::rotate_x(96);
    let scaled = yaw.mul(&pitch).scale_columns_q12([scale_q12, scale_q12, scale_q12]);
    scene::load_rotation(&scaled);

    let mut fi = 0usize;
    while fi < faces.len() {
        let (a,b,c) = faces[fi];
        let pa = scene::project_vertex(verts[a as usize]);
        let pb = scene::project_vertex(verts[b as usize]);
        let pc = scene::project_vertex(verts[c as usize]);
        if pa.sz > 64 && pb.sz > 64 && pc.sz > 64 &&
           pa.sx > -900 && pa.sx < 900 && pa.sy > -700 && pa.sy < 700 &&
           pb.sx > -900 && pb.sx < 900 && pb.sy > -700 && pb.sy < 700 &&
           pc.sx > -900 && pc.sx < 900 && pc.sy > -700 && pc.sy < 700 {
            draw_play11_textured_tri(
                [(pa.sx,pa.sy),(pb.sx,pb.sy),(pc.sx,pc.sy)],
                face_uvs[fi], PLAY11_UFO_TPAGE, PLAY11_UFO_CLUT,
            );
        }
        fi += 1;
    }
}

'''
s = s[:insert] + helper + s[insert:]

rep(
    '''    cam_x: i32,
    cam_z: i32,
) {''',
    '''    cam_x: i32,
    cam_z: i32,
    scale_q12: i32,
) {''',
    'render signature')

rep('            frame, yaw, view_x, world_y, view_z,\n        );',
    '            frame, yaw, view_x, world_y, view_z, scale_q12,\n        );',
    'ufo scale arg')
rep('            frame, yaw, view_x, world_y, view_z,\n        );',
    '            frame, yaw, view_x, world_y, view_z, scale_q12,\n        );',
    'zurg scale arg')

rep(
    '''    } else if model == 2 {
        render_play12_extra_flat(gpu,&TYRANT_VERTS,&TYRANT_FACES,frame,yaw,view_x,world_y,view_z,model);
    } else {
        render_play12_extra_flat(gpu,&TREX_VERTS,&TREX_FACES,frame,yaw,view_x,world_y,view_z,model);
    }''',
    '''    } else if model == 2 {
        render_play13b_extra_textured(&TYRANT_VERTS,&TYRANT_FACES,&TYRANT_UVS,frame,yaw,view_x,world_y,view_z,scale_q12);
    } else {
        render_play13b_extra_textured(&TREX_VERTS,&TREX_FACES,&TREX_UVS,frame,yaw,view_x,world_y,view_z,scale_q12);
    }''',
    'extra render')

rep(
    'font.draw_text(8, 190, "INERTIA + FOLLOW CAM   SQUARE = RATE", (0x68, 0x68, 0x70));',
    'font.draw_text(8, 190, "R2+L1/R1 = SCALE   L2 = RESET", (0x68, 0x68, 0x70));',
    'hud')

main.write_text(s)
print('3d_play13b: recovery renderer preserved; Tyrant/T-Rex textured; scale enabled')
