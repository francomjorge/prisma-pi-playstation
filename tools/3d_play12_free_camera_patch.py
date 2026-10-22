#!/usr/bin/env python3
from pathlib import Path
import sys

p = Path(sys.argv[1])
s = p.read_text()

def rep(old, new, label):
    global s
    if old not in s:
        raise SystemExit(f"3d_play12_free_camera_patch: {label} pattern not found")
    s = s.replace(old, new, 1)

rep(
'''    let mut gte_cam_x: i32 = 0;
    let mut gte_cam_z: i32 = 0;
    let mut gte_orbit_phase: u8 = 0;''',
'''    let mut gte_cam_x: i32 = 0;
    let mut gte_cam_y: i32 = 0;
    let mut gte_cam_z: i32 = 0;
    let mut gte_orbit_phase: u8 = 0;''',
"camera y state",
)

start = s.find('''                    let accel = match gte_rate {''')
end_marker = '''                    let turn = (gte_rate as u16) * 10;
                    if held(bits, button::L1) { gte_yaw = gte_yaw.wrapping_sub(turn); }
                    if held(bits, button::R1) { gte_yaw = gte_yaw.wrapping_add(turn); }'''
end = s.find(end_marker, start)
if start < 0 or end < 0:
    raise SystemExit("3d_play12_free_camera_patch: control block not found")
end += len(end_marker)
new_controls = r'''                    let accel = match gte_rate {
                        1 => 6i32,
                        2 => 11i32,
                        3 => 18i32,
                        4 => 28i32,
                        _ => 42i32,
                    };
                    let vmax = match gte_rate {
                        1 => 90i32,
                        2 => 150i32,
                        3 => 230i32,
                        4 => 330i32,
                        _ => 470i32,
                    };

                    let lr = held(bits, button::LEFT) || held(bits, button::RIGHT);
                    let fb = held(bits, button::UP) || held(bits, button::DOWN);
                    let ud = held(bits, button::TRIANGLE) || held(bits, button::CROSS);

                    if held(bits, button::LEFT)  { gte_vx -= accel; if gte_vx < -vmax { gte_vx = -vmax; } }
                    if held(bits, button::RIGHT) { gte_vx += accel; if gte_vx >  vmax { gte_vx =  vmax; } }
                    if held(bits, button::UP)    { gte_vz += accel; if gte_vz >  vmax { gte_vz =  vmax; } }
                    if held(bits, button::DOWN)  { gte_vz -= accel; if gte_vz < -vmax { gte_vz = -vmax; } }
                    if held(bits, button::TRIANGLE) { gte_vy -= accel; if gte_vy < -vmax { gte_vy = -vmax; } }
                    if held(bits, button::CROSS)    { gte_vy += accel; if gte_vy >  vmax { gte_vy =  vmax; } }

                    if !lr { gte_vx = (gte_vx * 7) / 8; }
                    if !fb { gte_vz = (gte_vz * 7) / 8; }
                    if !ud { gte_vy = (gte_vy * 7) / 8; }

                    gte_cam_x += gte_vx;
                    gte_cam_y += gte_vy;
                    gte_cam_z += gte_vz;

                    if gte_cam_x < -22000 { gte_cam_x = -22000; gte_vx = 0; }
                    if gte_cam_x >  22000 { gte_cam_x =  22000; gte_vx = 0; }
                    if gte_cam_y <  -9000 { gte_cam_y =  -9000; gte_vy = 0; }
                    if gte_cam_y >   9000 { gte_cam_y =   9000; gte_vy = 0; }
                    if gte_cam_z < -12000 { gte_cam_z = -12000; gte_vz = 0; }
                    if gte_cam_z >  36000 { gte_cam_z =  36000; gte_vz = 0; }

                    let turn = (gte_rate as u16) * 10;
                    if held(bits, button::L1) { gte_yaw = gte_yaw.wrapping_sub(turn); }
                    if held(bits, button::R1) { gte_yaw = gte_yaw.wrapping_add(turn); }'''
s = s[:start] + new_controls + s[end:]

rep(
'''            Screen::GteTest => render_gte_test(&font, &mut gpu, gte_frame, gte_model, gte_yaw, gte_auto, gte_rate, gte_x, gte_y, gte_z, gte_cam_x, gte_cam_z, gte_orbit_phase),''',
'''            Screen::GteTest => render_gte_test(&font, &mut gpu, gte_frame, gte_model, gte_yaw, gte_auto, gte_rate, gte_x, gte_y, gte_z, gte_cam_x, gte_cam_y, gte_cam_z, gte_orbit_phase),''',
"render call camera y",
)

rep(
'''    cam_x: i32,
    cam_z: i32,
    orbit_phase: u8,
) {''',
'''    cam_x: i32,
    cam_y: i32,
    cam_z: i32,
    orbit_phase: u8,
) {''',
"render signature camera y",
)

rep(
'''fn render_play12_floor(gpu: &mut Gpu, cam_x: i32, cam_z: i32) {
    scene::set_screen_offset(160 << 16, 112 << 16);
    scene::set_projection_plane(220);
    scene::load_rotation(&Mat3I16::rotate_y(0));
    scene::load_translation(Vec3I32::new(0, 0, 0x3A00));''',
'''fn render_play12_floor(gpu: &mut Gpu, cam_x: i32, cam_y: i32, cam_z: i32, cam_yaw: u16) {
    scene::set_screen_offset(160 << 16, 112 << 16);
    scene::set_projection_plane(220);
    scene::load_rotation(&Mat3I16::rotate_y((0u16).wrapping_sub(cam_yaw)));
    scene::load_translation(Vec3I32::new(0, -cam_y, 0x3A00));''',
"floor signature",
)

rep(
'''    render_play12_floor(gpu, cam_x, cam_z);

    let view_x = world_x - cam_x;
    let view_z = world_z - cam_z;''',
'''    render_play12_floor(gpu, cam_x, cam_y, cam_z, yaw);

    let center_x = world_x - cam_x;
    let center_z = world_z - cam_z;
    let view_y = world_y - cam_y;''',
"free camera center",
)

old_duo = '''    let ufo_x = view_x + PLAY12_ELLIPSE_X[oi];
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
    );'''
new_duo = '''    let ufo_dx = center_x + PLAY12_ELLIPSE_X[oi];
    let ufo_dz = center_z + PLAY12_ELLIPSE_Z[oi];
    let zurg_dx = center_x + PLAY12_ELLIPSE_X[oj];
    let zurg_dz = center_z + PLAY12_ELLIPSE_Z[oj];

    let ci = (((yaw as usize) >> 6) & 63) as usize;
    let cosv = PLAY12_ELLIPSE_X[ci];
    let sinv = PLAY12_ELLIPSE_Z[ci] * 2;

    let ufo_x = (ufo_dx * cosv + ufo_dz * sinv) / 3200;
    let ufo_z = (-ufo_dx * sinv + ufo_dz * cosv) / 3200;
    let zurg_x = (zurg_dx * cosv + zurg_dz * sinv) / 3200;
    let zurg_z = (-zurg_dx * sinv + zurg_dz * cosv) / 3200;

    render_play11_mesh(
        gpu, &UFO_VERTS, &UFO_FACES, &UFO_UVS,
        PLAY11_UFO_TPAGE, PLAY11_UFO_CLUT,
        frame, (orbit_phase as u16) * 6, ufo_x, view_y, ufo_z,
    );
    render_play11_mesh(
        gpu, &ZURG_VERTS, &ZURG_FACES, &ZURG_UVS,
        PLAY11_ZURG_TPAGE, PLAY11_ZURG_CLUT,
        frame, (0u16).wrapping_sub((orbit_phase as u16) * 5), zurg_x, view_y, zurg_z,
    );'''
rep(old_duo, new_duo, "camera-relative duo")

rep(
'''    write_command(pack_texcoord(uvs[0].0, uvs[0].1, clut.uv_word()));
    write_command(pack_vertex(verts[1].0, verts[1].1));
    write_command(pack_texcoord(uvs[1].0, uvs[1].1, tpage.uv_word(0)));
    write_command(pack_vertex(verts[2].0, verts[2].1));
    write_command(pack_texcoord(uvs[2].0, uvs[2].1, 0));''',
'''    write_command(pack_texcoord(uvs[0].0, 255u8.wrapping_sub(uvs[0].1), clut.uv_word()));
    write_command(pack_vertex(verts[1].0, verts[1].1));
    write_command(pack_texcoord(uvs[1].0, 255u8.wrapping_sub(uvs[1].1), tpage.uv_word(0)));
    write_command(pack_vertex(verts[2].0, verts[2].1));
    write_command(pack_texcoord(uvs[2].0, 255u8.wrapping_sub(uvs[2].1), 0));''',
"vertical texture flip",
)

rep(
'''    font.draw_text(8, 174, "D-PAD = THRUST    TRI/X = LIFT", (0x68, 0x68, 0x70));
    font.draw_text(8, 190, "INERTIA + FOLLOW CAM   SQUARE = RATE", (0x68, 0x68, 0x70));''',
'''    font.draw_text(8, 174, "D-PAD = CAMERA MOVE   TRI/X = CAMERA Y", (0x68, 0x68, 0x70));
    font.draw_text(8, 190, "L1/R1 = CAMERA TURN   SQUARE = RATE", (0x68, 0x68, 0x70));''',
"camera HUD",
)
rep(
'''    font.draw_text(8, 6, "3D PLAY 1.2 / DUO ELLIPSE", (0x70, 0xD0, 0xD0));''',
'''    font.draw_text(8, 6, "3D PLAY 1.3 / FREE CAMERA", (0x70, 0xD0, 0xD0));''',
"title",
)

p.write_text(s)
print("3d_play12_free_camera_patch: installed free camera + corrected vertical textures")
