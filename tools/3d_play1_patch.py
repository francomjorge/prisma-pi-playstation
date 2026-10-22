#!/usr/bin/env python3
from pathlib import Path
import sys

p = Path(sys.argv[1])
s = p.read_text()

def rep(old, new):
    global s
    if old not in s:
        raise SystemExit(f"3d_play1_patch: pattern not found: {old[:100]!r}")
    s = s.replace(old, new, 1)

rep(
    "use psx_gpu::prim::LineMono;",
    "use psx_gpu::prim::{LineMono, TriFlat};\nmod mesh3d;\nuse mesh3d::{UFO_VERTS, UFO_FACES, ZURG_VERTS, ZURG_FACES};",
)
rep(
    "    let mut gte_frame: u16 = 0;",
    "    let mut gte_frame: u16 = 0;\n    let mut gte_model: u8 = 0;\n    let mut gte_yaw: u16 = 0;\n    let mut gte_pitch: u16 = 0;\n    let mut gte_auto: bool = true;",
)
rep(
    "            Screen::GteTest => {\n                if just_pressed(pressed, button::CIRCLE) {\n                    screen = Screen::TestMenu;\n                }\n            }",
    "            Screen::GteTest => {\n                if just_pressed(pressed, button::CIRCLE) {\n                    screen = Screen::TestMenu;\n                } else {\n                    if just_pressed(pressed, button::SELECT) { gte_model ^= 1; }\n                    if just_pressed(pressed, button::START) { gte_auto = !gte_auto; }\n                    if held(bits, button::LEFT)  { gte_yaw = gte_yaw.wrapping_sub(24); }\n                    if held(bits, button::RIGHT) { gte_yaw = gte_yaw.wrapping_add(24); }\n                    if held(bits, button::UP)    { gte_pitch = gte_pitch.wrapping_sub(20); }\n                    if held(bits, button::DOWN)  { gte_pitch = gte_pitch.wrapping_add(20); }\n                }\n            }",
)
rep(
    "            Screen::GteTest => render_gte_test(&font, &mut gpu, gte_frame),",
    "            Screen::GteTest => render_gte_test(&font, &mut gpu, gte_frame, gte_model, gte_yaw, gte_pitch, gte_auto),",
)
rep(
    "        if screen == Screen::GteTest { gte_frame = gte_frame.wrapping_add(1); }",
    "        if screen == Screen::GteTest && gte_auto { gte_frame = gte_frame.wrapping_add(1); }",
)

marker = "// Documented PSoXide hello-gte baseline"
idx = s.find(marker)
if idx < 0:
    raise SystemExit("3d_play1_patch: GTE render marker not found")
s = s[:idx] + r'''// 3D PLAY 1 -- real PS1 asset geometry, flat-shaded first validation pass.
const PLAY1_MAX_VERTS: usize = 167;
const PLAY1_MAX_FACES: usize = 891;

fn render_play1_mesh(
    gpu: &mut Gpu,
    verts: &[Vec3I16],
    faces: &[(u16, u16, u16)],
    model: u8,
    frame: u16,
    yaw_manual: u16,
    pitch_manual: u16,
) {
    scene::set_screen_offset(160 << 16, 118 << 16);
    scene::set_projection_plane(220);
    scene::load_translation(Vec3I32::new(0, 0, 0x3600));

    let yaw = Mat3I16::rotate_y(yaw_manual.wrapping_add(frame.wrapping_mul(4)));
    let pitch = Mat3I16::rotate_x(pitch_manual.wrapping_add(frame.wrapping_mul(2)));
    scene::load_rotation(&yaw.mul(&pitch));

    let mut projected = [scene::Projected::default(); PLAY1_MAX_VERTS];
    let mut vi = 0usize;
    while vi < verts.len() {
        projected[vi] = scene::project_vertex(verts[vi]);
        vi += 1;
    }

    // Painter ordering without heap allocation: 256 linked depth buckets.
    let mut head = [-1i16; 256];
    let mut next = [-1i16; PLAY1_MAX_FACES];
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

            // Reject only extreme projection garbage. Backfaces are intentionally
            // kept in this first pass; painter ordering makes the closed mesh solid
            // and avoids relying on unknown source winding from ripped OBJ files.
            if pa.sx > -900 && pa.sx < 900 && pa.sy > -700 && pa.sy < 700 &&
               pb.sx > -900 && pb.sx < 900 && pb.sy > -700 && pb.sy < 700 &&
               pc.sx > -900 && pc.sx < 900 && pc.sy > -700 && pc.sy < 700 {
                let shade = 74u8.saturating_add(((255 - bucket as u8) >> 2) as u8);
                let (r, g, bcol) = if model == 0 {
                    (shade / 2, shade.saturating_add(70), shade.saturating_add(90))
                } else {
                    (shade.saturating_add(90), shade / 2, shade.saturating_add(24))
                };
                gpu.draw(&TriFlat::new(
                    [(pa.sx, pa.sy), (pb.sx, pb.sy), (pc.sx, pc.sy)],
                    r, g, bcol,
                ));
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
    pitch: u16,
    auto_rotate: bool,
) {
    if model == 0 {
        render_play1_mesh(gpu, &UFO_VERTS, &UFO_FACES, model, frame, yaw, pitch);
    } else {
        render_play1_mesh(gpu, &ZURG_VERTS, &ZURG_FACES, model, frame, yaw, pitch);
    }

    font.draw_text(8, 6, "3D PLAY 1", (0x70, 0xD0, 0xD0));
    if model == 0 {
        font.draw_text(8, 22, "MODEL: ALIEN MOTHERSHIP", (0x58, 0x90, 0x90));
        font.draw_text(8, 38, "145 VERTS / 753 TRIS", (0x58, 0x70, 0x70));
    } else {
        font.draw_text(8, 22, "MODEL: FLOATING ZURG ROBOT", (0x90, 0x58, 0x80));
        font.draw_text(8, 38, "167 VERTS / 891 TRIS", (0x70, 0x58, 0x68));
    }
    font.draw_text(8, 186, "SELECT = MODEL   D-PAD = ROTATE", (0x68, 0x68, 0x70));
    if auto_rotate {
        font.draw_text(8, 202, "START = AUTO OFF", (0x60, 0xA0, 0x70));
    } else {
        font.draw_text(8, 202, "START = AUTO ON", (0xA0, 0x80, 0x60));
    }
    font.draw_text(8, 218, "CIRCLE = BACK", (0x58, 0x58, 0x60));
}
'''

p.write_text(s)
print("3d_play1_patch: installed UFO/Zurg mesh viewer")
