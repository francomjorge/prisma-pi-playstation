#!/usr/bin/env python3
import pathlib
import sys

path = pathlib.Path(sys.argv[1])
s = path.read_text()

old = '''    if selection == 0 {
        draw_outline(18, 171, 142, 49, cyan);
        let scan_x = 21 + ((frame / 2) % 132) as i16;
        draw_rect(scan_x, 172, 8, 1, (0xD0, 0xF8, 0xFF));
    } else {
        draw_outline(160, 171, 143, 49, magenta);
        let scan_x = 163 + ((frame / 2) % 132) as i16;
        draw_rect(scan_x, 172, 8, 1, (0xFF, 0x90, 0xE8));
    }
'''

new = '''    // Selection follows the actual chamfered card silhouette in the 320x240 artwork.
    // These coordinates were measured on the quantized HOME asset, not guessed as a box.
    if selection == 0 {
        draw_chamfer_selector(19, 177, 147, 42, 7, cyan);
        draw_side_chevron(10, 198, true, cyan);
    } else {
        draw_chamfer_selector(168, 177, 137, 42, 7, magenta);
        draw_side_chevron(310, 198, false, magenta);
    }
'''

if old not in s:
    raise SystemExit('selector patch failed: render selection block not found')
s = s.replace(old, new, 1)

old_helper = '''fn draw_outline(x: i16, y: i16, w: u16, h: u16, color: (u8, u8, u8)) {
    draw_rect(x, y, w, 1, color);
    draw_rect(x, y + h as i16 - 1, w, 1, color);
    draw_rect(x, y, 1, h, color);
    draw_rect(x + w as i16 - 1, y, 1, h, color);
}
'''

new_helper = '''fn draw_chamfer_selector(
    x: i16,
    y: i16,
    w: u16,
    h: u16,
    cut: u16,
    color: (u8, u8, u8),
) {
    let wi = w as i16;
    let hi = h as i16;
    let ci = cut as i16;

    // Straight sections of the octagonal/chamfered bezel.
    draw_rect(x + ci, y, w - cut * 2, 1, color);
    draw_rect(x + ci, y + hi - 1, w - cut * 2, 1, color);
    draw_rect(x, y + ci, 1, h - cut * 2, color);
    draw_rect(x + wi - 1, y + ci, 1, h - cut * 2, color);

    // Four pixel diagonals make the animated selector follow the actual button corners.
    let mut i: i16 = 0;
    while i < ci {
        draw_rect(x + i, y + ci - i, 1, 1, color);
        draw_rect(x + wi - 1 - i, y + ci - i, 1, 1, color);
        draw_rect(x + i, y + hi - 1 - ci + i, 1, 1, color);
        draw_rect(x + wi - 1 - i, y + hi - 1 - ci + i, 1, 1, color);
        i += 1;
    }
}

fn draw_side_chevron(x: i16, y: i16, points_right: bool, color: (u8, u8, u8)) {
    // Small animated navigation cue outside the active card. It moves with LEFT / RIGHT.
    let mut i: i16 = 0;
    while i < 7 {
        let dx = if points_right { i } else { -i };
        draw_rect(x + dx, y - i, 1, 1, color);
        draw_rect(x + dx, y + i, 1, 1, color);
        i += 1;
    }
}
'''

if old_helper not in s:
    raise SystemExit('selector patch failed: rectangular outline helper not found')
s = s.replace(old_helper, new_helper, 1)

path.write_text(s)
print(f'Applied chamfer-matched HOME selector to {path}')
