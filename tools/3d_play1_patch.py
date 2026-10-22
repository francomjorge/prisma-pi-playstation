#!/usr/bin/env python3
from pathlib import Path
import sys

p = Path(sys.argv[1])
s = p.read_text()

def rep(old, new):
    global s
    if old not in s:
        raise SystemExit(f"3d_play11_patch: pattern not found: {old[:120]!r}")
    s = s.replace(old, new, 1)

# Imports + mesh/UV data.
rep(
    "use psx_gpu::prim::LineMono;",
    "use psx_gpu::prim::LineMono;\nmod mesh3d;\nuse mesh3d::{UFO_VERTS, UFO_FACES, UFO_UVS, ZURG_VERTS, ZURG_FACES, ZURG_UVS};",
)

# Dedicated top-right VRAM pages, clear of framebuffers and the existing UI atlas.
rep(
    "const FONT_CLUT: Clut = Clut::new(320, 256);",
    '''const FONT_CLUT: Clut = Clut::new(320, 256);

// 3D PLAY 1.1 textures: original 256x256 indexed texture pages from the supplied assets.
// Each file = 65536 8bpp texel indices + 512-byte 256-entry RGB555 CLUT.
static PLAY11_UFO_TEX: &[u8] = include_bytes!("play11_ufo_tex.bin");
static PLAY11_ZURG_TEX: &[u8] = include_bytes!("play11_zurg_tex.bin");
const PLAY11_TEX_PIXELS: usize = 256 * 256;
const PLAY11_UFO_TPAGE: TexturePage = TexturePage::new(768, 0, TextureDepth::Bit8);
const PLAY11_ZURG_TPAGE: TexturePage = TexturePage::new(896, 0, TextureDepth::Bit8);
const PLAY11_UFO_CLUT: Clut = Clut::new(256, 497);
const PLAY11_ZURG_CLUT: Clut = Clut::new(512, 497);''',
)

# Upload the textures once at boot.
rep(
    "    upload_prisma_image();",
    "    upload_prisma_image();\n    upload_play11_textures();",
)

# Runtime 3D state.
rep(
    "    let mut gte_frame: u16 = 0;",
    '''    let mut gte_frame: u16 = 0;
    let mut gte_model: u8 = 0;
    let mut gte_yaw: u16 = 0;
    let mut gte_auto: bool = true;
    let mut gte_rate: u8 = 2;
    let mut gte_x: i32 = 0;
    let mut gte_y: i32 = 0;
    let mut gte_z: i32 = 0x3600;''',
)

# Controls: translate on the plane, altitude, yaw, rate, model and autorotation.
rep(
    '''            Screen::GteTest => {
                if just_pressed(pressed, button::CIRCLE) {
                    screen = Screen::TestMenu;
                }
            }''',
    '''            Screen::GteTest => {
                if just_pressed(pressed, button::CIRCLE) {
                    screen = Screen::TestMenu;
                } else {
                    if just_pressed(pressed, button::SELECT) { gte_model ^= 1; }
                    if just_pressed(pressed, button::START) { gte_auto = !gte_auto; }
                    if just_pressed(pressed, button::SQUARE) {
                        gte_rate = if gte_rate >= 5 { 1 } else { gte_rate + 1 };
                    }

                    let step = match gte_rate {
                        1 => 48i32,
                        2 => 96i32,
                        3 => 160i32,
                        4 => 240i32,
                        _ => 360i32,
                    };

                    if held(bits, button::LEFT) && gte_x > -7600 { gte_x -= step; }
                    if held(bits, button::RIGHT) && gte_x < 7600 { gte_x += step; }
                    // UP moves away into the perspective field, DOWN moves toward camera.
                    if held(bits, button::UP) && gte_z < 0x7000 { gte_z += step; }
                    if held(bits, button::DOWN) && gte_z > 0x2200 { gte_z -= step; }
                    // Triangle/Cross control altitude independently of the ground plane.
                    if held(bits, button::TRIANGLE) && gte_y > -5200 { gte_y -= step; }
                    if held(bits, button::CROSS) && gte_y < 5200 { gte_y += step; }

                    let turn = (gte_rate as u16) * 10;
                    if held(bits, button::L1) { gte_yaw = gte_yaw.wrapping_sub(turn); }
                    if held(bits, button::R1) { gte_yaw = gte_yaw.wrapping_add(turn); }
                }
            }''',
)

rep(
    "            Screen::GteTest => render_gte_test(&font, &mut gpu, gte_frame),",
    "            Screen::GteTest => render_gte_test(&font, &mut gpu, gte_frame, gte_model, gte_yaw, gte_auto, gte_rate, gte_x, gte_y, gte_z),",
)

rep(
    "        if screen == Screen::GteTest { gte_frame = gte_frame.wrapping_add(1); }",
    "        if screen == Screen::GteTest && gte_auto { gte_frame = gte_frame.wrapping_add(gte_rate as u16); }",
)

# Replace the baseline cube implementation appended by gte_test_patch.py.
marker = "// Documented PSoXide hello-gte baseline"
idx = s.find(marker)
if idx < 0:
    raise SystemExit("3d_play11_patch: GTE render marker not found")

s = s[:idx] + r'''// 3D PLAY 1.1 -- textured PS1 assets + movement on a perspective ground plane.
const PLAY11_MAX_VERTS: usize = 167;
const PLAY11_MAX_FACES: usize = 891;

fn upload_play11_textures() {
    // 8bpp: 256 texels occupy 128 VRAM halfwords per row.
    let ufo_rect = VramRect::new(PLAY11_UFO_TPAGE.x(), PLAY11_UFO_TPAGE.y(), 128, 256);
    upload_bytes(ufo_rect, &PLAY11_UFO_TEX[..PLAY11_TEX_PIXELS]);
    let ufo_clut_rect = VramRect::new(PLAY11_UFO_CLUT.x(), PLAY11_UFO_CLUT.y(), 256, 1);
    upload_bytes(ufo_clut_rect, &PLAY11_UFO_TEX[PLAY11_TEX_PIXELS..]);

    let zurg_rect = VramRect::new(PLAY11_ZURG_TPAGE.x(), PLAY11_ZURG_TPAGE.y(), 128, 256);
    upload_bytes(zurg_rect, &PLAY11_ZURG_TEX[..PLAY11_TEX_PIXELS]);
    let zurg_clut_rect = VramRect::new(PLAY11_ZURG_CLUT.x(), PLAY11_ZURG_CLUT.y(), 256, 1);
    upload_bytes(zurg_clut_rect, &PLAY11_ZURG_TEX[PLAY11_TEX_PIXELS..]);
}

fn draw_play11_textured_tri(
    verts: [(i16, i16); 3],
    uvs: [(u8, u8); 3],
    tpage: TexturePage,
    clut: Clut,
) {
    // GP0(24h): flat-textured triangle. 0x80 tint = source texel at 1.0x.
    wait_command_ready();
    write_command(psx_hw::gpu::packet::FLAT_TEXTURED_TRIANGLE | pack_color(0x80, 0x80, 0x80));
    write_command(pack_vertex(verts[0].0, verts[0].1));
    write_command(pack_texcoord(uvs[0].0, uvs[0].1, clut.uv_word()));
    write_command(pack_vertex(verts[1].0, verts[1].1));
    write_command(pack_texcoord(uvs[1].0, uvs[1].1, tpage.uv_word(0)));
    write_command(pack_vertex(verts[2].0, verts[2].1));
    write_command(pack_texcoord(uvs[2].0, uvs[2].1, 0));
}

fn render_play11_floor(gpu: &mut Gpu) {
    scene::set_screen_offset(160 << 16, 112 << 16);
    scene::set_projection_plane(220);
    scene::load_rotation(&Mat3I16::rotate_y(0));
    scene::load_translation(Vec3I32::new(0, 0, 0x3A00));

    // A small world-space grid. Near lines are brighter, far lines dimmer.
    let mut zi = 0i16;
    while zi < 9 {
        let z = -6200 + zi * 3000;
        let a = scene::project_vertex(Vec3I16::new(-12000, 3000, z));
        let b = scene::project_vertex(Vec3I16::new(12000, 3000, z));
        let bright = 82u8.saturating_sub((zi as u8) * 5);
        gpu.draw(&LineMono::new(a.sx, a.sy, b.sx, b.sy, bright / 2, bright, bright));
        zi += 1;
    }

    let mut xi = 0i16;
    while xi < 9 {
        let x = -12000 + xi * 3000;
        let a = scene::project_vertex(Vec3I16::new(x, 3000, -6200));
        let b = scene::project_vertex(Vec3I16::new(x, 3000, 17800));
        gpu.draw(&LineMono::new(a.sx, a.sy, b.sx, b.sy, 34, 58, 66));
        xi += 1;
    }
}

fn render_play11_mesh(
    gpu: &mut Gpu,
    verts: &[Vec3I16],
    faces: &[(u16, u16, u16)],
    face_uvs: &[[(u8, u8); 3]],
    tpage: TexturePage,
    clut: Clut,
    frame: u16,
    yaw_manual: u16,
    world_x: i32,
    world_y: i32,
    world_z: i32,
) {
    scene::set_screen_offset(160 << 16, 112 << 16);
    scene::set_projection_plane(220);
    scene::load_translation(Vec3I32::new(world_x, world_y, world_z));

    let yaw = Mat3I16::rotate_y(yaw_manual.wrapping_add(frame.wrapping_mul(4)));
    // Small fixed pitch makes the shape readable while translation remains independent.
    let pitch = Mat3I16::rotate_x(96);
    scene::load_rotation(&yaw.mul(&pitch));

    let mut projected = [scene::Projected::default(); PLAY11_MAX_VERTS];
    let mut vi = 0usize;
    while vi < verts.len() {
        projected[vi] = scene::project_vertex(verts[vi]);
        vi += 1;
    }

    // Painter ordering: 256 linked depth buckets, no heap allocation.
    let mut head = [-1i16; 256];
    let mut next = [-1i16; PLAY11_MAX_FACES];
    let mut fi = 0usize;
    while fi < faces.len() {
        let (a, b, c) = faces[fi];
        let pa = projected[a as usize];
        let pb = projected[b as usize];
        let pc = projected[c as usize];
        let avg = ((pa.sz as u32 + pb.sz as u32 + pc.sz as u32) / 3) as u16;
        let mut bucket = (avg >> 6) as usize;
        if bucket > 255 { bucket = 255; }
        next[fi] = head[bucket];
        head[bucket] = fi as i16;
        fi += 1;
    }

    let mut bucket = 255i16;
    while bucket >= 0 {
        let mut cur = head[bucket as usize];
        while cur >= 0 {
            let i = cur as usize;
            let (a, b, c) = faces[i];
            let pa = projected[a as usize];
            let pb = projected[b as usize];
            let pc = projected[c as usize];

            if pa.sx > -900 && pa.sx < 900 && pa.sy > -700 && pa.sy < 700 &&
               pb.sx > -900 && pb.sx < 900 && pb.sy > -700 && pb.sy < 700 &&
               pc.sx > -900 && pc.sx < 900 && pc.sy > -700 && pc.sy < 700 {
                draw_play11_textured_tri(
                    [(pa.sx, pa.sy), (pb.sx, pb.sy), (pc.sx, pc.sy)],
                    face_uvs[i],
                    tpage,
                    clut,
                );
            }
            cur = next[i];
        }
        bucket -= 1;
    }
}

fn render_gte_test(
    font: &FontAtlas,
    gpu: &mut Gpu,
    frame: u16,
    model: u8,
    yaw: u16,
    auto_rotate: bool,
    rate: u8,
    world_x: i32,
    world_y: i32,
    world_z: i32,
) {
    render_play11_floor(gpu);

    if model == 0 {
        render_play11_mesh(
            gpu, &UFO_VERTS, &UFO_FACES, &UFO_UVS,
            PLAY11_UFO_TPAGE, PLAY11_UFO_CLUT,
            frame, yaw, world_x, world_y, world_z,
        );
    } else {
        render_play11_mesh(
            gpu, &ZURG_VERTS, &ZURG_FACES, &ZURG_UVS,
            PLAY11_ZURG_TPAGE, PLAY11_ZURG_CLUT,
            frame, yaw, world_x, world_y, world_z,
        );
    }

    font.draw_text(8, 6, "3D PLAY 1.1 / TEXTURED", (0x70, 0xD0, 0xD0));
    if model == 0 {
        font.draw_text(8, 22, "ALIEN MOTHERSHIP / 753 TRI", (0x58, 0x90, 0x90));
    } else {
        font.draw_text(8, 22, "FLOATING ZURG / 891 TRI", (0x90, 0x58, 0x80));
    }
    const RATE_LABELS: [&str; 5] = ["RATE 1", "RATE 2", "RATE 3", "RATE 4", "RATE 5"];
    font.draw_text(250, 6, RATE_LABELS[(rate.saturating_sub(1).min(4)) as usize], (0xA0, 0xA0, 0x70));

    font.draw_text(8, 174, "D-PAD = X / DEPTH    TRI/X = HEIGHT", (0x68, 0x68, 0x70));
    font.draw_text(8, 190, "L1/R1 = TURN   SQUARE = RATE", (0x68, 0x68, 0x70));
    font.draw_text(8, 206, "SELECT = MODEL", (0x68, 0x68, 0x70));
    if auto_rotate {
        font.draw_text(160, 206, "START = AUTO OFF", (0x60, 0xA0, 0x70));
    } else {
        font.draw_text(160, 206, "START = AUTO ON", (0xA0, 0x80, 0x60));
    }
    font.draw_text(8, 222, "CIRCLE = BACK", (0x58, 0x58, 0x60));
}
'''

p.write_text(s)
print("3d_play11_patch: installed textured movement viewer")
