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

# Runs after gte_test_patch.py. Installs the addressable Asset Lab browser.
rep("use psx_font::{fonts::BASIC, FontAtlas};", "use psx_font::{fonts::BASIC, BitOrder, BitmapFont, FontAtlas};")
rep("const FONT_CLUT: Clut = Clut::new(320, 256);", "const FONT_CLUT: Clut = Clut::new(320, 256);\nconst CP437_TPAGE: TexturePage = TexturePage::new(384, 0, TextureDepth::Bit4);\nconst CP437_CLUT: Clut = Clut::new(336, 256);\nstatic CP437_BITMAP: &[u8; 2048] = include_bytes!(\"cp437_8x8.bin\");\nconst CP437_FONT: BitmapFont = BitmapFont { glyph_w: 8, glyph_h: 8, first_char: 0, glyph_count: 256, bitmap: CP437_BITMAP, glyph_advances: None, advance_x: 8, line_height: 8, bit_order: BitOrder::Msb };" )
rep("    GteTest,\n    CdTest,", "    GteTest,\n    AssetLab,\n    CdTest,")
rep("    let mut gte_frame: u16 = 0;", "    let mut gte_frame: u16 = 0;\n    let cp437_font = FontAtlas::upload(&CP437_FONT, CP437_TPAGE, CP437_CLUT);\n    let mut asset_index: u8 = 0;\n    let mut asset_frame: u8 = 0;\n    let mut asset_playing: bool = false;")
rep("test_selection = if test_selection == 0 { 6 } else { test_selection - 1 };", "test_selection = if test_selection == 0 { 7 } else { test_selection - 1 };")
rep("test_selection = if test_selection >= 6 { 0 } else { test_selection + 1 };", "test_selection = if test_selection >= 7 { 0 } else { test_selection + 1 };")
rep("                        3 => { gte_frame = 0; Screen::GteTest },\n                        4 => Screen::CdTest,\n                        5 => Screen::MemoryTest,", "                        3 => { gte_frame = 0; Screen::GteTest },\n                        4 => { asset_index = 0; asset_frame = 0; asset_playing = false; Screen::AssetLab },\n                        5 => Screen::CdTest,\n                        6 => Screen::MemoryTest,")
rep("            Screen::GteTest => {\n                if just_pressed(pressed, button::CIRCLE) {\n                    screen = Screen::TestMenu;\n                }\n            }", "            Screen::GteTest => {\n                if just_pressed(pressed, button::CIRCLE) { screen = Screen::TestMenu; }\n            }\n            Screen::AssetLab => {\n                if just_pressed(pressed, button::CIRCLE) {\n                    screen = Screen::TestMenu;\n                } else {\n                    if just_pressed(pressed, button::SELECT) || just_pressed(pressed, button::RIGHT) { asset_index = if asset_index + 1 >= ASSET_COUNT { 0 } else { asset_index + 1 }; asset_frame = 0; }\n                    if just_pressed(pressed, button::LEFT) { asset_index = if asset_index == 0 { ASSET_COUNT - 1 } else { asset_index - 1 }; asset_frame = 0; }\n                    if just_pressed(pressed, button::SQUARE) { asset_frame = asset_frame.wrapping_sub(1) & 7; }\n                    if just_pressed(pressed, button::CROSS) { asset_playing = !asset_playing; }\n                }\n            }")
rep("            Screen::GteTest => (0, 0, 12),", "            Screen::GteTest => (0, 0, 12),\n            Screen::AssetLab => (2, 4, 10),")
rep("            Screen::GteTest => render_gte_test(&font, &mut gpu, gte_frame),", "            Screen::GteTest => render_gte_test(&font, &mut gpu, gte_frame),\n            Screen::AssetLab => render_asset_lab(&font, &cp437_font, asset_index, asset_frame, asset_playing),")
rep("        if screen == Screen::GteTest { gte_frame = gte_frame.wrapping_add(1); }", "        if screen == Screen::GteTest { gte_frame = gte_frame.wrapping_add(1); }\n        if screen == Screen::AssetLab && asset_playing && (gte_frame & 7) == 0 { asset_frame = asset_frame.wrapping_add(1) & 7; }\n        if screen == Screen::AssetLab { gte_frame = gte_frame.wrapping_add(1); }")
rep('    const ITEMS: [&str; 7] = [\n        "CONTROLLER MAP",\n        "IMAGE / VRAM",\n        "AUDIO / SPU",\n        "3D / GTE",\n        "CD / STREAM",\n        "MEMORY CARD",\n        "BACK",\n    ];\n    let mut i: u8 = 0;\n    while i < 7 {', '    const ITEMS: [&str; 8] = [\n        "CONTROLLER MAP",\n        "IMAGE / VRAM",\n        "AUDIO / SPU",\n        "3D / GTE",\n        "ASSET LAB",\n        "CD / STREAM",\n        "MEMORY CARD",\n        "BACK",\n    ];\n    let mut i: u8 = 0;\n    while i < 8 {')

s += r'''

#[derive(Clone, Copy)]
struct AssetEntry {
    id: u16,
    name: &'static str,
    kind: &'static str,
    size: &'static str,
    frames: u8,
}

const ASSETS: [AssetEntry; 24] = [
    AssetEntry { id: 0x0000, name: "FONT_PIXEL_TECH", kind: "FONT", size: "8x8", frames: 1 },
    AssetEntry { id: 0x0001, name: "FONT_PRISMA", kind: "FONT", size: "16x16", frames: 1 },
    AssetEntry { id: 0x0002, name: "CP437_SYMBOLS", kind: "FONT", size: "8x8", frames: 1 },
    AssetEntry { id: 0x0010, name: "UI_BUTTON", kind: "SPRITE", size: "32x16", frames: 4 },
    AssetEntry { id: 0x0011, name: "UI_KNOB", kind: "SPRITE", size: "32x32", frames: 8 },
    AssetEntry { id: 0x0012, name: "UI_PROGRESS", kind: "SPRITE", size: "96x12", frames: 8 },
    AssetEntry { id: 0x0013, name: "UI_LED", kind: "SPRITE", size: "16x16", frames: 4 },
    AssetEntry { id: 0x0014, name: "UI_SELECTOR", kind: "SPRITE", size: "32x16", frames: 4 },
    AssetEntry { id: 0x0020, name: "TEX_METAL", kind: "TEXTURE", size: "64x64", frames: 1 },
    AssetEntry { id: 0x0021, name: "TEX_WOOD", kind: "TEXTURE", size: "64x64", frames: 1 },
    AssetEntry { id: 0x0022, name: "TEX_BRICK", kind: "TEXTURE", size: "64x64", frames: 1 },
    AssetEntry { id: 0x0023, name: "TEX_STONE", kind: "TEXTURE", size: "64x64", frames: 1 },
    AssetEntry { id: 0x0024, name: "TEX_HAZARD", kind: "TEXTURE", size: "64x64", frames: 1 },
    AssetEntry { id: 0x0025, name: "TEX_GRID", kind: "TEXTURE", size: "64x64", frames: 1 },
    AssetEntry { id: 0x0026, name: "TEX_RADAR", kind: "TEXTURE", size: "64x64", frames: 1 },
    AssetEntry { id: 0x0027, name: "TEX_BARS", kind: "TEXTURE", size: "64x64", frames: 1 },
    AssetEntry { id: 0x0028, name: "TEX_TECH", kind: "TEXTURE", size: "64x64", frames: 1 },
    AssetEntry { id: 0x0029, name: "TEX_STARS", kind: "TEXTURE", size: "64x64", frames: 1 },
    AssetEntry { id: 0x0030, name: "BG_BUDDHA", kind: "BACKGROUND", size: "320x240", frames: 1 },
    AssetEntry { id: 0x0031, name: "BG_SPACE", kind: "BACKGROUND", size: "320x240", frames: 1 },
    AssetEntry { id: 0x0040, name: "GHOST_ASCII_8", kind: "SPRITE", size: "8x8", frames: 8 },
    AssetEntry { id: 0x0041, name: "GHOST_ASCII_16", kind: "SPRITE", size: "16x16", frames: 8 },
    AssetEntry { id: 0x0042, name: "GHOST_ASCII_24", kind: "SPRITE", size: "24x24", frames: 8 },
    AssetEntry { id: 0x0043, name: "GHOST_ASCII_32", kind: "SPRITE", size: "32x32", frames: 8 },
];
const ASSET_COUNT: u8 = ASSETS.len() as u8;

fn draw_hex4(font: &FontAtlas, x: i16, y: i16, value: u16, color: (u8,u8,u8)) {
    const HEX: &[u8; 16] = b"0123456789ABCDEF";
    let bytes = [HEX[((value >> 12) & 15) as usize], HEX[((value >> 8) & 15) as usize], HEX[((value >> 4) & 15) as usize], HEX[(value & 15) as usize]];
    if let Ok(t) = core::str::from_utf8(&bytes) { font.draw_text(x, y, t, color); }
}

fn draw_cp437_grid(cp437: &FontAtlas) {
    // PSoXide's text API accepts Unicode, while CP437 is a byte code page.
    // Map byte values 0..255 to matching codepoints because this atlas is
    // deliberately declared first_char=0/glyph_count=256. Control-code glyphs
    // are therefore drawable too. 16x16 cells = the complete ROM table.
    let mut code: u16 = 0;
    while code < 256 {
        let row = code / 16;
        let col = code & 15;
        let ch = char::from_u32(code as u32).unwrap_or(' ');
        let mut utf8 = [0u8; 4];
        let text = ch.encode_utf8(&mut utf8);
        cp437.draw_text(176 + (col as i16 * 8), 52 + (row as i16 * 8), text, (0xD0, 0xD0, 0xD0));
        code += 1;
    }
}

fn render_asset_lab(font: &FontAtlas, cp437: &FontAtlas, index: u8, frame: u8, playing: bool) {
    let a = ASSETS[index as usize];
    font.draw_text(8, 8, "TEST / ASSET BROWSER", (0x70, 0xD0, 0xD0));
    font.draw_text(8, 28, a.name, (0xD0, 0xB0, 0x40));
    font.draw_text(8, 50, "ASSET ID: 0x", (0x70, 0x70, 0x78));
    draw_hex4(font, 112, 50, a.id, (0xD0, 0xD0, 0xD0));
    font.draw_text(8, 66, "TYPE:", (0x70, 0x70, 0x78));
    font.draw_text(56, 66, a.kind, (0x90, 0xC0, 0xD0));
    font.draw_text(8, 82, "SIZE:", (0x70, 0x70, 0x78));
    font.draw_text(56, 82, a.size, (0x90, 0xC0, 0xD0));
    if a.id == 0x0002 {
        font.draw_text(8, 98, "COOKED: 2048 BYTES", (0x60, 0xC0, 0x80));
        font.draw_text(176, 36, "CP437 00-FF", (0x70, 0xD0, 0xD0));
        draw_cp437_grid(cp437);
    } else {
        font.draw_text(8, 98, "ADDRESSABLE: YES", (0x60, 0xC0, 0x80));
    }
    font.draw_text(8, 114, "FRAME:", (0x70, 0x70, 0x78));
    let f = if a.frames <= 1 { 0 } else { frame % a.frames };
    let fb = [b'0' + f];
    if let Ok(t) = core::str::from_utf8(&fb) { font.draw_text(64, 114, t, (0xD0, 0xD0, 0xD0)); }
    font.draw_text(88, 114, if playing { "PLAY" } else { "STOP" }, (0xB0, 0x80, 0xD0));
    font.draw_text(8, 146, "SELECT/RIGHT = NEXT ASSET", (0x58, 0x70, 0x78));
    font.draw_text(8, 162, "LEFT = PREVIOUS ASSET", (0x58, 0x70, 0x78));
    font.draw_text(8, 178, "SQUARE = PREV FRAME", (0x58, 0x70, 0x78));
    font.draw_text(8, 194, "CROSS = PLAY/STOP", (0x58, 0x70, 0x78));
    font.draw_text(8, 220, "CIRCLE = BACK", (0x58, 0x58, 0x60));
}
'''

p.write_text(s)
print("asset_lab_patch: installed Asset Browser + cooked CP437 renderer")
