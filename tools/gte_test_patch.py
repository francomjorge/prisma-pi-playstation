#!/usr/bin/env python3
from pathlib import Path
import sys

p = Path(sys.argv[1])
s = p.read_text()

def rep(old, new):
    global s
    if old not in s:
        raise SystemExit(f"gte_test_patch: pattern not found: {old[:80]!r}")
    s = s.replace(old, new, 1)

rep("use psx_gpu::Gpu;", "use psx_gpu::Gpu;\nuse psx_gpu::prim::LineMono;\nuse psx_gte::math::{Mat3I16, Vec3I16, Vec3I32};\nuse psx_gte::scene;")
rep("    AudioTest,\n    CdTest,", "    AudioTest,\n    GteTest,\n    CdTest,")
rep("    let mut audio = AudioTestState::INIT;", "    let mut audio = AudioTestState::INIT;\n    let mut gte_frame: u16 = 0;")
rep("test_selection = if test_selection == 0 { 5 } else { test_selection - 1 };", "test_selection = if test_selection == 0 { 6 } else { test_selection - 1 };")
rep("test_selection = if test_selection >= 5 { 0 } else { test_selection + 1 };", "test_selection = if test_selection >= 6 { 0 } else { test_selection + 1 };")
rep("                        2 => Screen::AudioTest,\n                        3 => Screen::CdTest,\n                        4 => Screen::MemoryTest,", "                        2 => Screen::AudioTest,\n                        3 => { gte_frame = 0; Screen::GteTest },\n                        4 => Screen::CdTest,\n                        5 => Screen::MemoryTest,")
rep("            Screen::CdTest | Screen::MemoryTest => {", "            Screen::GteTest => {\n                if just_pressed(pressed, button::CIRCLE) {\n                    screen = Screen::TestMenu;\n                }\n            }\n            Screen::CdTest | Screen::MemoryTest => {")
rep("            Screen::CdTest => (4, 6, 12),", "            Screen::GteTest => (0, 0, 12),\n            Screen::CdTest => (4, 6, 12),")
rep("            Screen::AudioTest => render_audio_test(&font, &audio),", "            Screen::AudioTest => render_audio_test(&font, &audio),\n            Screen::GteTest => render_gte_test(&font, &mut gpu, gte_frame),")
rep("        previous_bits = bits;", "        previous_bits = bits;\n        if screen == Screen::GteTest { gte_frame = gte_frame.wrapping_add(1); }")
rep('    const ITEMS: [&str; 6] = [\n        "CONTROLLER MAP",\n        "IMAGE / VRAM",\n        "AUDIO / SPU",\n        "CD / STREAM",\n        "MEMORY CARD",\n        "BACK",\n    ];\n    let mut i: u8 = 0;\n    while i < 6 {', '    const ITEMS: [&str; 7] = [\n        "CONTROLLER MAP",\n        "IMAGE / VRAM",\n        "AUDIO / SPU",\n        "3D / GTE",\n        "CD / STREAM",\n        "MEMORY CARD",\n        "BACK",\n    ];\n    let mut i: u8 = 0;\n    while i < 7 {')

s += r'''

// Documented PSoXide hello-gte baseline: 8 vertices, 12 edges, RTPS projection.
const GTE_CUBE_VERTS: [Vec3I16; 8] = [
    Vec3I16::new(-0x0800, -0x0800, -0x0800),
    Vec3I16::new( 0x0800, -0x0800, -0x0800),
    Vec3I16::new( 0x0800,  0x0800, -0x0800),
    Vec3I16::new(-0x0800,  0x0800, -0x0800),
    Vec3I16::new(-0x0800, -0x0800,  0x0800),
    Vec3I16::new( 0x0800, -0x0800,  0x0800),
    Vec3I16::new( 0x0800,  0x0800,  0x0800),
    Vec3I16::new(-0x0800,  0x0800,  0x0800),
];
const GTE_CUBE_EDGES: [(usize, usize); 12] = [
    (0,1),(1,2),(2,3),(3,0),(4,5),(5,6),(6,7),(7,4),(0,4),(1,5),(2,6),(3,7),
];

fn render_gte_test(font: &FontAtlas, gpu: &mut Gpu, frame: u16) {
    scene::set_screen_offset(160 << 16, 120 << 16);
    scene::set_projection_plane(200);
    scene::load_translation(Vec3I32::new(0, 0, 0x3000));
    let yaw = Mat3I16::rotate_y(frame.wrapping_mul(4));
    let pitch = Mat3I16::rotate_x(frame.wrapping_mul(3));
    scene::load_rotation(&yaw.mul(&pitch));

    let mut projected = [(0i16, 0i16); 8];
    for (i, v) in GTE_CUBE_VERTS.iter().enumerate() {
        let q = scene::project_vertex(*v);
        projected[i] = (q.sx, q.sy);
    }
    for &(a, b) in &GTE_CUBE_EDGES {
        let (ax, ay) = projected[a];
        let (bx, by) = projected[b];
        gpu.draw(&LineMono::new(ax, ay, bx, by, 255, 255, 255));
    }

    font.draw_text(8, 6, "TEST / 3D / GTE", (0x70, 0xD0, 0xD0));
    font.draw_text(8, 22, "PSoXide hello-gte baseline", (0x58, 0x70, 0x70));
    font.draw_text(8, 174, "GTE: ACTIVE", (0x60, 0xC0, 0x80));
    font.draw_text(8, 188, "VERTICES: 8   EDGES: 12", (0x70, 0x70, 0x78));
    font.draw_text(8, 202, "RTPS / PERSPECTIVE / LINE GPU", (0x70, 0x70, 0x78));
    font.draw_text(8, 220, "CIRCLE = BACK", (0x58, 0x58, 0x60));
}
'''

p.write_text(s)
print("gte_test_patch: installed 3D/GTE menu test")
