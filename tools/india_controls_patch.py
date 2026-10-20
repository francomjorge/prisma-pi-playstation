#!/usr/bin/env python3
import pathlib
import sys

path = pathlib.Path(sys.argv[1])
s = path.read_text()

old = '''const INDIA_CLUT_OFFSET: usize = INDIA_LEFT_BYTES + INDIA_RIGHT_BYTES;\n'''
new = '''const INDIA_CLUT_OFFSET: usize = INDIA_LEFT_BYTES + INDIA_RIGHT_BYTES;\n\n// Tiny INDIA UI atlas: 11 numeric sprites (00..100), 128x32, 8-bit indexed.\n// Palette index 0 is transparent so the digits sit cleanly over the baked panel.\nstatic INDIA_UI_ASSET: &[u8] = include_bytes!(\"india_ui_ps1.bin\");\nconst INDIA_UI_PIXELS: usize = 128 * 32;\nconst INDIA_UI_TPAGE: TexturePage = TexturePage::new(704, 0, TextureDepth::Bit8);\nconst INDIA_UI_CLUT: Clut = Clut::new(0, 497);\n'''
if old not in s:
    raise SystemExit('india controls patch failed: constants anchor not found')
s = s.replace(old, new, 1)

old = '''    let mut prisma_selection: u8 = 0;\n'''
new = '''    let mut prisma_selection: u8 = 0;\n    // Values are stored as 0..10 and rendered as 00..100.\n    let mut prisma_values: [u8; 6] = [4, 4, 4, 4, 4, 4];\n'''
if old not in s:
    raise SystemExit('india controls patch failed: prisma state anchor not found')
s = s.replace(old, new, 1)

old = '''                        upload_india_image();\n                        screen = Screen::Prisma;\n'''
new = '''                        upload_india_image();\n                        upload_india_ui();\n                        screen = Screen::Prisma;\n'''
if old not in s:
    raise SystemExit('india controls patch failed: INDIA entry anchor not found')
s = s.replace(old, new, 1)

old = '''                if just_pressed(pressed, button::UP) || just_pressed(pressed, button::DOWN) {\n                    prisma_selection = if prisma_selection < 3 {\n                        prisma_selection + 3\n                    } else {\n                        prisma_selection - 3\n                    };\n                }\n                if just_pressed(pressed, button::CIRCLE) {\n'''
new = '''                if just_pressed(pressed, button::UP) || just_pressed(pressed, button::DOWN) {\n                    prisma_selection = if prisma_selection < 3 {\n                        prisma_selection + 3\n                    } else {\n                        prisma_selection - 3\n                    };\n                }\n\n                // First live instrument control layer. CROSS raises the selected\n                // channel by 10; SQUARE lowers it by 10. Navigation remains on D-pad.\n                let value_index = prisma_selection as usize;\n                if just_pressed(pressed, button::CROSS) && prisma_values[value_index] < 10 {\n                    prisma_values[value_index] += 1;\n                }\n                if just_pressed(pressed, button::SQUARE) && prisma_values[value_index] > 0 {\n                    prisma_values[value_index] -= 1;\n                }\n\n                if just_pressed(pressed, button::CIRCLE) {\n'''
if old not in s:
    raise SystemExit('india controls patch failed: Prisma input anchor not found')
s = s.replace(old, new, 1)

old = '''            Screen::Prisma => render_india(prisma_selection, frame_counter),\n'''
new = '''            Screen::Prisma => render_india(prisma_selection, frame_counter, &prisma_values),\n'''
if old not in s:
    raise SystemExit('india controls patch failed: render arm not found')
s = s.replace(old, new, 1)

anchor = '''fn upload_india_image() {\n'''
insert = '''fn upload_india_ui() {\n    // 8bpp atlas: 128 texels = 64 VRAM words.\n    let pixel_rect = VramRect::new(INDIA_UI_TPAGE.x(), INDIA_UI_TPAGE.y(), 64, 32);\n    upload_bytes(pixel_rect, &INDIA_UI_ASSET[..INDIA_UI_PIXELS]);\n\n    let clut_rect = VramRect::new(INDIA_UI_CLUT.x(), INDIA_UI_CLUT.y(), 256, 1);\n    upload_bytes(clut_rect, &INDIA_UI_ASSET[INDIA_UI_PIXELS..]);\n}\n\nfn draw_india_number(value: u8, x: i16, y: i16) {\n    let v = if value > 10 { 10 } else { value };\n    let col = v % 6;\n    let row = v / 6;\n    let u = col * 21;\n    let vv = row * 14;\n\n    INDIA_UI_TPAGE.apply_as_draw_mode();\n    wait_command_ready();\n    write_command(psx_hw::gpu::packet::TEXTURED_RECT | pack_color(0x80, 0x80, 0x80));\n    write_command(pack_vertex(x, y));\n    write_command(pack_texcoord(u, vv, INDIA_UI_CLUT.uv_word()));\n    write_command(pack_xy(20, 12));\n}\n\nfn draw_india_channel_value(panel_x: i16, panel_y: i16, value: u8, selected: bool, frame: u32) {\n    // Cover the baked 40/bar data but keep the original panel frame and label.\n    let bar_x = panel_x + 7;\n    let bar_y = panel_y + 18;\n    let num_x = panel_x + 78;\n    let num_y = panel_y + 18;\n\n    draw_rect(bar_x, bar_y, 66, 12, (0x10, 0x10, 0x16));\n    draw_rect(num_x, num_y, 20, 12, (0x10, 0x10, 0x18));\n\n    let pulse = selected && ((frame / 8) & 1) == 0;\n    let fill = if pulse { (0xFF, 0xD0, 0x18) } else { (0xF0, 0xA8, 0x08) };\n    let glow = if pulse { (0xFF, 0xF0, 0x70) } else { (0xFF, 0xC8, 0x20) };\n\n    let mut seg = 0u8;\n    while seg < 10 {\n        let sx = bar_x + 2 + (seg as i16 * 6);\n        if seg < value {\n            draw_rect(sx, bar_y + 2, 5, 8, fill);\n            draw_rect(sx, bar_y + 2, 5, 1, glow);\n        } else {\n            draw_rect(sx, bar_y + 2, 5, 8, (0x18, 0x18, 0x20));\n        }\n        seg += 1;\n    }\n\n    draw_india_number(value, num_x, num_y);\n}\n\nfn upload_india_image() {\n'''
if anchor not in s:
    raise SystemExit('india controls patch failed: upload_india_image anchor not found')
s = s.replace(anchor, insert, 1)

old = '''fn render_india(selection: u8, frame: u32) {\n    draw_india_image();\n\n    // Pixel-matched selector around the six baked module panels.\n    const X: [i16; 3] = [8, 110, 212];\n    const Y: [i16; 2] = [156, 194];\n    let row = (selection / 3) as usize;\n    let col = (selection % 3) as usize;\n    let x = X[col];\n    let y = Y[row];\n\n    let bright = ((frame / 10) & 1) == 0;\n'''
new = '''fn render_india(selection: u8, frame: u32, values: &[u8; 6]) {\n    draw_india_image();\n\n    // Pixel-matched panel origins for the six baked module panels.\n    const X: [i16; 3] = [8, 110, 212];\n    const Y: [i16; 2] = [156, 194];\n\n    let mut i = 0usize;\n    while i < 6 {\n        let r = i / 3;\n        let c = i % 3;\n        draw_india_channel_value(X[c], Y[r], values[i], i == selection as usize, frame);\n        i += 1;\n    }\n\n    let row = (selection / 3) as usize;\n    let col = (selection % 3) as usize;\n    let x = X[col];\n    let y = Y[row];\n\n    let bright = ((frame / 10) & 1) == 0;\n'''
if old not in s:
    raise SystemExit('india controls patch failed: render_india block not found')
s = s.replace(old, new, 1)

path.write_text(s)
print(f'Applied live INDIA values + 10-segment bars to {path}')
