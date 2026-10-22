#!/usr/bin/env python3
from pathlib import Path
import sys

p = Path(sys.argv[1])
s = p.read_text()

def rep(old, new, label):
    global s
    if old not in s:
        raise SystemExit(f"3d_play12_duo_ellipse_patch: {label} pattern not found")
    s = s.replace(old, new, 1)

# Independent orbital phase; camera/movement state stays exactly as PLAY 1.2.
rep(
'''    let mut gte_cam_x: i32 = 0;
    let mut gte_cam_z: i32 = 0;''',
'''    let mut gte_cam_x: i32 = 0;
    let mut gte_cam_z: i32 = 0;
    let mut gte_orbit_phase: u8 = 0;''',
"orbit state",
)

rep(
'''            Screen::GteTest => render_gte_test(&font, &mut gpu, gte_frame, gte_model, gte_yaw, gte_auto, gte_rate, gte_x, gte_y, gte_z, gte_cam_x, gte_cam_z),''',
'''            Screen::GteTest => render_gte_test(&font, &mut gpu, gte_frame, gte_model, gte_yaw, gte_auto, gte_rate, gte_x, gte_y, gte_z, gte_cam_x, gte_cam_z, gte_orbit_phase),''',
"render call",
)

rep(
'''        if screen == Screen::GteTest && gte_auto { gte_frame = gte_frame.wrapping_add(gte_rate as u16); }''',
'''        if screen == Screen::GteTest && gte_auto { gte_frame = gte_frame.wrapping_add(gte_rate as u16); }
        if screen == Screen::GteTest { gte_orbit_phase = gte_orbit_phase.wrapping_add(gte_rate); }''',
"orbit tick",
)

# Insert a tiny fixed-point ellipse lookup before the main GTE render function.
marker = '''fn render_gte_test(
'''
idx = s.find(marker)
if idx < 0:
    raise SystemExit("3d_play12_duo_ellipse_patch: render marker not found")
lookup = r'''const PLAY12_ELLIPSE_X: [i32; 64] = [
    3200,3185,3139,3062,2956,2822,2661,2474,2263,2030,1778,1508,1225,929,624,314,
    0,-314,-624,-929,-1225,-1508,-1778,-2030,-2263,-2474,-2661,-2822,-2956,-3062,-3139,-3185,
    -3200,-3185,-3139,-3062,-2956,-2822,-2661,-2474,-2263,-2030,-1778,-1508,-1225,-929,-624,-314,
    0,314,624,929,1225,1508,1778,2030,2263,2474,2661,2822,2956,3062,3139,3185
];
const PLAY12_ELLIPSE_Z: [i32; 64] = [
    0,147,293,435,574,707,833,952,1061,1160,1247,1323,1386,1435,1471,1493,
    1500,1493,1471,1435,1386,1323,1247,1160,1061,952,833,707,574,435,293,147,
    0,-147,-293,-435,-574,-707,-833,-952,-1061,-1160,-1247,-1323,-1386,-1435,-1471,-1493,
    -1500,-1493,-1471,-1435,-1386,-1323,-1247,-1160,-1061,-952,-833,-707,-574,-435,-293,-147
];

'''
s = s[:idx] + lookup + s[idx:]

rep(
'''    cam_x: i32,
    cam_z: i32,
) {''',
'''    cam_x: i32,
    cam_z: i32,
    orbit_phase: u8,
) {''',
"render signature",
)

old = '''    if model == 0 {
        render_play11_mesh(
            gpu, &UFO_VERTS, &UFO_FACES, &UFO_UVS,
            PLAY11_UFO_TPAGE, PLAY11_UFO_CLUT,
            frame, yaw, view_x, world_y, view_z,
        );
    } else {
        render_play11_mesh(
            gpu, &ZURG_VERTS, &ZURG_FACES, &ZURG_UVS,
            PLAY11_ZURG_TPAGE, PLAY11_ZURG_CLUT,
            frame, yaw, view_x, world_y, view_z,
        );
    }
'''
new = '''    // Duo mode: both validated textured assets are always visible.
    // They remain opposite each other (180 degrees) on an ellipse centered on the
    // same movable PLAY 1.2 world position. The D-pad therefore moves the ellipse
    // center while the two models keep orbiting automatically.
    let oi = ((orbit_phase >> 1) & 63) as usize;
    let oj = (oi + 32) & 63;

    let ufo_x = view_x + PLAY12_ELLIPSE_X[oi];
    let ufo_z = view_z + PLAY12_ELLIPSE_Z[oi];
    let zurg_x = view_x + PLAY12_ELLIPSE_X[oj];
    let zurg_z = view_z + PLAY12_ELLIPSE_Z[oj];

    render_play11_mesh(
        gpu, &UFO_VERTS, &UFO_FACES, &UFO_UVS,
        PLAY11_UFO_TPAGE, PLAY11_UFO_CLUT,
        frame, yaw.wrapping_add((orbit_phase as u16) * 6), ufo_x, world_y, ufo_z,
    );
    render_play11_mesh(
        gpu, &ZURG_VERTS, &ZURG_FACES, &ZURG_UVS,
        PLAY11_ZURG_TPAGE, PLAY11_ZURG_CLUT,
        frame, yaw.wrapping_sub((orbit_phase as u16) * 5), zurg_x, world_y, zurg_z,
    );
'''
rep(old, new, "dual render")

rep(
'''    font.draw_text(8, 6, "3D PLAY 1.2 / FLIGHT", (0x70, 0xD0, 0xD0));''',
'''    font.draw_text(8, 6, "3D PLAY 1.2 / DUO ELLIPSE", (0x70, 0xD0, 0xD0));''',
"title",
)

# Replace the model-specific status line with a fixed duo label.
old_hud = '''    if model == 0 {
        font.draw_text(8, 22, "ALIEN MOTHERSHIP / 753 TRI", (0x58, 0x90, 0x90));
    } else {
        font.draw_text(8, 22, "FLOATING ZURG / 891 TRI", (0x90, 0x58, 0x80));
    }'''
new_hud = '''    font.draw_text(8, 22, "ALIEN + ZURG / AUTO ELLIPSE", (0x78, 0x98, 0xA0));'''
rep(old_hud, new_hud, "duo hud")

# SELECT no longer swaps models because both are shown at once; keep the rest untouched.
rep(
'''                    if just_pressed(pressed, button::SELECT) { gte_model ^= 1; }''',
'''                    if just_pressed(pressed, button::SELECT) { gte_orbit_phase = gte_orbit_phase.wrapping_add(32); }''',
"select behavior",
)

rep(
'''    font.draw_text(8, 206, "SELECT = MODEL", (0x68, 0x68, 0x70));''',
'''    font.draw_text(8, 206, "SELECT = SWAP SIDES", (0x68, 0x68, 0x70));''',
"select hud",
)

p.write_text(s)
print("3d_play12_duo_ellipse_patch: installed Alien + Zurg elliptical duo mode")
