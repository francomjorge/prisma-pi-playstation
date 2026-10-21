#!/usr/bin/env python3
import pathlib
import sys

path = pathlib.Path(sys.argv[1])
s = path.read_text()

# The title animation deliberately does NOT use a second letter sprite anymore.
# Instead it reads the exact indexed pixels already baked into INDIA_ASSET and
# recolors only the warm fill pixels of the first six glyphs (P R I S M A).
# The original outline/shadow, the hyphen, PI and INDIA therefore stay perfectly
# registered with the master artwork at native 320x240.

anchor = '''fn upload_india_ui() {\n'''
insert = '''fn india_asset_index(x: usize, y: usize) -> u8 {
    if x < 256 {
        INDIA_ASSET[y * 256 + x]
    } else {
        INDIA_ASSET[INDIA_LEFT_BYTES + y * 64 + (x - 256)]
    }
}

fn india_palette_word(index: u8) -> u16 {
    let o = INDIA_CLUT_OFFSET + (index as usize) * 2;
    (INDIA_ASSET[o] as u16) | ((INDIA_ASSET[o + 1] as u16) << 8)
}

fn prisma_warm_pixel(x: usize, y: usize) -> bool {
    let word = india_palette_word(india_asset_index(x, y));
    let r = word & 31;
    let g = (word >> 5) & 31;
    let b = (word >> 10) & 31;

    // Select the orange/yellow/red body of the title while rejecting the blue
    // sky and the dark navy outline/shadow. These are RGB555 thresholds.
    r >= 15 && g >= 3 && r > b + 4 && (r + g) >= 20
}

fn prisma_word_end() -> i16 {
    // Discover the first six glyph groups directly from the baked title. A
    // two-column blank tolerance prevents tiny quantization gaps from splitting
    // a letter. The next group is the hyphen, which is intentionally excluded.
    let mut x: usize = 166;
    let mut glyphs: u8 = 0;
    let mut in_glyph = false;
    let mut blank_cols: u8 = 3;
    let mut last_warm_x: usize = 166;

    while x < 318 {
        let mut y: usize = 21;
        let mut warm = false;
        while y < 53 {
            if prisma_warm_pixel(x, y) {
                warm = true;
                break;
            }
            y += 1;
        }

        if warm {
            if !in_glyph && blank_cols >= 2 {
                glyphs += 1;
                if glyphs > 6 {
                    break;
                }
            }
            in_glyph = true;
            blank_cols = 0;
            last_warm_x = x;
        } else if in_glyph {
            blank_cols = blank_cols.saturating_add(1);
            if blank_cols >= 2 {
                in_glyph = false;
            }
        } else {
            blank_cols = blank_cols.saturating_add(1);
        }
        x += 1;
    }

    (last_warm_x + 1) as i16
}

fn prisma_fire_color(x: i16, y: i16, frame: u32) -> (u8, u8, u8) {
    // Moving vertical/diagonal heat bands. Geometry never moves: only the
    // color inside the exact original letter pixels changes.
    let phase = ((y as u32 * 3 + x as u32 + frame * 3) % 24) as u8;
    match phase {
        0..=4 => (0xFF, 0xF0, 0x78),
        5..=9 => (0xFF, 0xC8, 0x28),
        10..=14 => (0xFF, 0x88, 0x08),
        15..=19 => (0xE8, 0x40, 0x08),
        _ => (0xB8, 0x18, 0x10),
    }
}

fn draw_prisma_fire(frame: u32) {
    const X0: i16 = 166;
    const Y0: i16 = 21;
    const Y1: i16 = 53;
    let x1 = prisma_word_end();

    // Draw horizontal runs rather than individual pixels. This keeps the exact
    // baked silhouette while reducing GPU commands substantially.
    let mut y = Y0;
    while y < Y1 {
        let mut x = X0;
        while x < x1 {
            if prisma_warm_pixel(x as usize, y as usize) {
                let start = x;
                let color = prisma_fire_color(x, y, frame);
                x += 1;
                while x < x1 && prisma_warm_pixel(x as usize, y as usize) {
                    x += 1;
                }
                draw_rect(start, y, (x - start) as u16, 1, color);
            } else {
                x += 1;
            }
        }
        y += 1;
    }
}

fn upload_india_ui() {\n'''
if anchor not in s:
    raise SystemExit('prisma fire patch failed: upload_india_ui anchor not found')
s = s.replace(anchor, insert, 1)

old = '''fn render_india(selection: u8, frame: u32, values: &[u8; 6]) {\n    draw_india_image();\n'''
new = '''fn render_india(selection: u8, frame: u32, values: &[u8; 6]) {\n    draw_india_image();\n    // Animate the exact baked PRISMA pixels. -PI and INDIA remain static.\n    draw_prisma_fire(frame);\n'''
if old not in s:
    raise SystemExit('prisma fire patch failed: render_india anchor not found')
s = s.replace(old, new, 1)

path.write_text(s)
print(f'Applied pixel-registered PRISMA fire animation to {path}')
