#!/usr/bin/env python3
from pathlib import Path
import sys

p = Path(sys.argv[1])
s = p.read_text()

def rep(old, new):
    global s
    if old not in s:
        raise SystemExit(f"asset_lab_patch: pattern not found: {old[:100]!r}")
    s = s.replace(old, new, 1)

# This patch intentionally comes after gte_test_patch.py and only adds a
# lightweight diagnostic browser. Binary art assets are added separately.
rep("    GteTest,\n    CdTest,", "    GteTest,\n    AssetLab,\n    CdTest,")
rep("    let mut gte_frame: u16 = 0;", "    let mut gte_frame: u16 = 0;\n    let mut asset_page: u8 = 0;\n    let mut asset_frame: u8 = 0;")
rep("test_selection = if test_selection == 0 { 6 } else { test_selection - 1 };", "test_selection = if test_selection == 0 { 7 } else { test_selection - 1 };")
rep("test_selection = if test_selection >= 6 { 0 } else { test_selection + 1 };", "test_selection = if test_selection >= 7 { 0 } else { test_selection + 1 };")
rep("                        3 => { gte_frame = 0; Screen::GteTest },\n                        4 => Screen::CdTest,\n                        5 => Screen::MemoryTest,", "                        3 => { gte_frame = 0; Screen::GteTest },\n                        4 => { asset_page = 0; asset_frame = 0; Screen::AssetLab },\n                        5 => Screen::CdTest,\n                        6 => Screen::MemoryTest,")
rep("            Screen::GteTest => {\n                if just_pressed(pressed, button::CIRCLE) {\n                    screen = Screen::TestMenu;\n                }\n            }", "            Screen::GteTest => {\n                if just_pressed(pressed, button::CIRCLE) { screen = Screen::TestMenu; }\n            }\n            Screen::AssetLab => {\n                if just_pressed(pressed, button::CIRCLE) {\n                    screen = Screen::TestMenu;\n                } else {\n                    if just_pressed(pressed, button::LEFT) { asset_page = if asset_page == 0 { 5 } else { asset_page - 1 }; }\n                    if just_pressed(pressed, button::RIGHT) { asset_page = if asset_page >= 5 { 0 } else { asset_page + 1 }; }\n                    if just_pressed(pressed, button::SQUARE) { asset_frame = asset_frame.wrapping_sub(1) & 7; }\n                    if just_pressed(pressed, button::CROSS) { asset_frame = asset_frame.wrapping_add(1) & 7; }\n                }\n            }")
rep("            Screen::GteTest => (0, 0, 12),", "            Screen::GteTest => (0, 0, 12),\n            Screen::AssetLab => (2, 4, 10),")
rep("            Screen::GteTest => render_gte_test(&font, &mut gpu, gte_frame),", "            Screen::GteTest => render_gte_test(&font, &mut gpu, gte_frame),\n            Screen::AssetLab => render_asset_lab(&font, asset_page, asset_frame),")
rep('    const ITEMS: [&str; 7] = [\n        "CONTROLLER MAP",\n        "IMAGE / VRAM",\n        "AUDIO / SPU",\n        "3D / GTE",\n        "CD / STREAM",\n        "MEMORY CARD",\n        "BACK",\n    ];\n    let mut i: u8 = 0;\n    while i < 7 {', '    const ITEMS: [&str; 8] = [\n        "CONTROLLER MAP",\n        "IMAGE / VRAM",\n        "AUDIO / SPU",\n        "3D / GTE",\n        "ASSET LAB",\n        "CD / STREAM",\n        "MEMORY CARD",\n        "BACK",\n    ];\n    let mut i: u8 = 0;\n    while i < 8 {')

s += r'''

fn render_asset_lab(font: &FontAtlas, page: u8, frame: u8) {
    const PAGES: [&str; 6] = [
        "FONT / CP437",
        "UI CONTROLS",
        "PROGRESS / METERS",
        "TEXTURES / MATERIALS",
        "BACKGROUNDS",
        "GHOST / SPRITES",
    ];
    font.draw_text(8, 8, "TEST / ASSET LAB", (0x70, 0xD0, 0xD0));
    font.draw_text(8, 26, PAGES[page as usize], (0xD0, 0xB0, 0x40));
    font.draw_text(8, 50, "ASSET LIBRARY READY", (0x60, 0xC0, 0x80));
    font.draw_text(8, 68, "FONT: PIXEL TECH 8x8", (0x90, 0x90, 0x98));
    font.draw_text(8, 82, "FONT: PRISMA 16x16", (0x90, 0x90, 0x98));
    font.draw_text(8, 96, "CP437 / ICONS / UI", (0x90, 0x90, 0x98));
    font.draw_text(8, 110, "BARS / KNOBS / SELECTORS", (0x90, 0x90, 0x98));
    font.draw_text(8, 124, "10 TEXTURES / 2 BACKGROUNDS", (0x90, 0x90, 0x98));
    font.draw_text(8, 138, "GHOST 8/16/24/32 + 8 FRAMES", (0x90, 0x90, 0x98));
    font.draw_text(8, 162, "FRAME", (0x60, 0x90, 0xC0));
    let digit = [b'0' + frame];
    if let Ok(t) = core::str::from_utf8(&digit) { font.draw_text(56, 162, t, (0xD0, 0xD0, 0xD0)); }
    font.draw_text(8, 192, "LEFT/RIGHT = CATEGORY", (0x58, 0x70, 0x78));
    font.draw_text(8, 206, "SQUARE/CROSS = FRAME", (0x58, 0x70, 0x78));
    font.draw_text(8, 220, "CIRCLE = BACK", (0x58, 0x58, 0x60));
}
'''

p.write_text(s)
print("asset_lab_patch: installed Asset Lab diagnostic")
