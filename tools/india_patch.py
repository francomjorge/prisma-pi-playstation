#!/usr/bin/env python3
import pathlib
import sys

path = pathlib.Path(sys.argv[1])
s = path.read_text()

# INDIA reuses HOME's two 8-bit texture pages in VRAM. We swap the image when
# entering/leaving PRISMA-PI instead of reserving another full 320x240 texture.
old = '''const HOME_CLUT: Clut = Clut::new(512, 496);\n'''
new = '''const HOME_CLUT: Clut = Clut::new(512, 496);\n\n// PRISMA-PI INDIA: 320x240, 8-bit indexed + 256-entry RGB555 CLUT.\n// It is uploaded into the same VRAM pages used by HOME when the instrument\n// is entered, then HOME is restored on CIRCLE.\nstatic INDIA_ASSET: &[u8] = include_bytes!(\"india_ps1.bin\");\nconst INDIA_LEFT_BYTES: usize = 256 * 240;\nconst INDIA_RIGHT_BYTES: usize = 64 * 240;\nconst INDIA_CLUT_OFFSET: usize = INDIA_LEFT_BYTES + INDIA_RIGHT_BYTES;\n'''
if old not in s:
    raise SystemExit('india patch failed: HOME_CLUT anchor not found')
s = s.replace(old, new, 1)

old = '''    let mut home_selection: u8 = 0;\n'''
new = '''    let mut home_selection: u8 = 0;\n    let mut prisma_selection: u8 = 0;\n'''
if old not in s:
    raise SystemExit('india patch failed: state anchor not found')
s = s.replace(old, new, 1)

old = '''                if confirm_pressed(pressed) {\n                    screen = if home_selection == 0 { Screen::Prisma } else { Screen::TestMenu };\n                }\n'''
new = '''                if confirm_pressed(pressed) {\n                    if home_selection == 0 {\n                        prisma_selection = 0;\n                        upload_india_image();\n                        screen = Screen::Prisma;\n                    } else {\n                        screen = Screen::TestMenu;\n                    }\n                }\n'''
if old not in s:
    raise SystemExit('india patch failed: HOME confirm block not found')
s = s.replace(old, new, 1)

old = '''            Screen::Prisma => {\n                if just_pressed(pressed, button::CIRCLE) {\n                    screen = Screen::Home;\n                }\n            }\n'''
new = '''            Screen::Prisma => {\n                // INDIA is a 2x3 module grid:\n                // DRUM 1 / DRUM 2 / BASS\n                // KEYS   / SITAR  / LEAD\n                if just_pressed(pressed, button::LEFT) {\n                    let row = prisma_selection / 3;\n                    let col = prisma_selection % 3;\n                    prisma_selection = row * 3 + ((col + 2) % 3);\n                }\n                if just_pressed(pressed, button::RIGHT) {\n                    let row = prisma_selection / 3;\n                    let col = prisma_selection % 3;\n                    prisma_selection = row * 3 + ((col + 1) % 3);\n                }\n                if just_pressed(pressed, button::UP) || just_pressed(pressed, button::DOWN) {\n                    prisma_selection = if prisma_selection < 3 {\n                        prisma_selection + 3\n                    } else {\n                        prisma_selection - 3\n                    };\n                }\n                if just_pressed(pressed, button::CIRCLE) {\n                    upload_home_image();\n                    screen = Screen::Home;\n                }\n            }\n'''
if old not in s:
    raise SystemExit('india patch failed: Prisma controls block not found')
s = s.replace(old, new, 1)

old = '''            Screen::Prisma => render_prisma(&font),\n'''
new = '''            Screen::Prisma => render_india(prisma_selection, frame_counter),\n'''
if old not in s:
    raise SystemExit('india patch failed: Prisma render arm not found')
s = s.replace(old, new, 1)

anchor = '''fn upload_home_image() {\n'''
insert = '''fn upload_india_image() {\n    // Reuse HOME's VRAM pages: 8bpp = two texels per VRAM word.\n    let left_rect = VramRect::new(\n        HOME_TPAGE_LEFT.x(),\n        HOME_TPAGE_LEFT.y(),\n        128,\n        240,\n    );\n    upload_bytes(left_rect, &INDIA_ASSET[..INDIA_LEFT_BYTES]);\n\n    let right_rect = VramRect::new(\n        HOME_TPAGE_RIGHT.x(),\n        HOME_TPAGE_RIGHT.y(),\n        32,\n        240,\n    );\n    upload_bytes(\n        right_rect,\n        &INDIA_ASSET[INDIA_LEFT_BYTES..INDIA_CLUT_OFFSET],\n    );\n\n    let clut_rect = VramRect::new(HOME_CLUT.x(), HOME_CLUT.y(), 256, 1);\n    upload_bytes(clut_rect, &INDIA_ASSET[INDIA_CLUT_OFFSET..]);\n}\n\nfn draw_india_image() {\n    HOME_TPAGE_LEFT.apply_as_draw_mode();\n    wait_command_ready();\n    write_command(psx_hw::gpu::packet::TEXTURED_RECT | pack_color(0x80, 0x80, 0x80));\n    write_command(pack_vertex(0, 0));\n    write_command(pack_texcoord(0, 0, HOME_CLUT.uv_word()));\n    write_command(pack_xy(256, 240));\n\n    HOME_TPAGE_RIGHT.apply_as_draw_mode();\n    wait_command_ready();\n    write_command(psx_hw::gpu::packet::TEXTURED_RECT | pack_color(0x80, 0x80, 0x80));\n    write_command(pack_vertex(256, 0));\n    write_command(pack_texcoord(0, 0, HOME_CLUT.uv_word()));\n    write_command(pack_xy(64, 240));\n}\n\nfn render_india(selection: u8, frame: u32) {\n    draw_india_image();\n\n    // Pixel-matched selector around the six baked module panels.\n    const X: [i16; 3] = [8, 110, 212];\n    const Y: [i16; 2] = [156, 194];\n    let row = (selection / 3) as usize;\n    let col = (selection % 3) as usize;\n    let x = X[col];\n    let y = Y[row];\n\n    let bright = ((frame / 10) & 1) == 0;\n    let outer = if bright { (0xFF, 0xE0, 0x38) } else { (0xF0, 0x80, 0x18) };\n    let inner = if bright { (0xFF, 0xFF, 0xB0) } else { (0xF8, 0xC0, 0x30) };\n    draw_chamfer_selector(x, y, 100, 37, 3, outer);\n    draw_chamfer_selector(x + 1, y + 1, 98, 35, 2, inner);\n}\n\nfn upload_home_image() {\n'''
if anchor not in s:
    raise SystemExit('india patch failed: upload_home_image anchor not found')
s = s.replace(anchor, insert, 1)

path.write_text(s)
print(f'Applied PRISMA-PI INDIA 2x3 navigable instrument screen to {path}')
