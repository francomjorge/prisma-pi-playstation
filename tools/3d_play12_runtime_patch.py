#!/usr/bin/env python3
from pathlib import Path
import sys

p = Path(sys.argv[1])
s = p.read_text()

def rep(old, new, label):
    global s
    if old not in s:
        raise SystemExit(f"3d_play12_runtime_patch: {label} pattern not found")
    s = s.replace(old, new, 1)

rep(
'''    let mut gte_rate: u8 = 2;
    let mut gte_x: i32 = 0;
    let mut gte_y: i32 = 0;
    let mut gte_z: i32 = 0x3600;''',
'''    let mut gte_rate: u8 = 2;
    let mut gte_x: i32 = 0;
    let mut gte_y: i32 = 0;
    let mut gte_z: i32 = 0x3600;
    let mut gte_vx: i32 = 0;
    let mut gte_vy: i32 = 0;
    let mut gte_vz: i32 = 0;
    let mut gte_cam_x: i32 = 0;
    let mut gte_cam_z: i32 = 0;''',
"runtime state",
)

old_controls = '''                    let step = match gte_rate {
                        1 => 48i32,
                        2 => 96i32,
                        3 => 160i32,
                        4 => 240i32,
                        _ => 360i32,
                    };

                    if held(bits, button::LEFT) && gte_x > -7600 { gte_x -= step; }
                    if held(bits, button::RIGHT) && gte_x < 7600 { gte_x += step; }
                    // UP moves away into the perspective field, DOWN moves toward camera.
                    if held(bits, button::UP) && gte_z < 0x7000 { gte_z += step; }
                    if held(bits, button::DOWN) && gte_z > 0x2200 { gte_z -= step; }
                    // Triangle/Cross control altitude independently of the ground plane.
                    if held(bits, button::TRIANGLE) && gte_y > -5200 { gte_y -= step; }
                    if held(bits, button::CROSS) && gte_y < 5200 { gte_y += step; }

                    let turn = (gte_rate as u16) * 10;
                    if held(bits, button::L1) { gte_yaw = gte_yaw.wrapping_sub(turn); }
                    if held(bits, button::R1) { gte_yaw = gte_yaw.wrapping_add(turn); }'''
new_controls = '''                    let accel = match gte_rate {
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

                    // Friction only on axes without active thrust. 7/8 gives a clearly visible coast.
                    if !lr { gte_vx = (gte_vx * 7) / 8; }
                    if !fb { gte_vz = (gte_vz * 7) / 8; }
                    if !ud { gte_vy = (gte_vy * 7) / 8; }

                    gte_x += gte_vx;
                    gte_y += gte_vy;
                    gte_z += gte_vz;

                    if gte_x < -18000 { gte_x = -18000; gte_vx = 0; }
                    if gte_x >  18000 { gte_x =  18000; gte_vx = 0; }
                    if gte_y <  -6200 { gte_y =  -6200; gte_vy = 0; }
                    if gte_y >   6200 { gte_y =   6200; gte_vy = 0; }
                    if gte_z <   0x1800 { gte_z = 0x1800; gte_vz = 0; }
                    if gte_z >   0xB000 { gte_z = 0xB000; gte_vz = 0; }

                    // Follow camera: strong enough to keep the model readable, slow enough to show drift.
                    gte_cam_x += (gte_x - gte_cam_x) / 7;
                    let cam_z_target = gte_z - 0x3600;
                    gte_cam_z += (cam_z_target - gte_cam_z) / 9;

                    let turn = (gte_rate as u16) * 10;
                    if held(bits, button::L1) { gte_yaw = gte_yaw.wrapping_sub(turn); }
                    if held(bits, button::R1) { gte_yaw = gte_yaw.wrapping_add(turn); }'''
rep(old_controls, new_controls, "controls")

rep(
'''            Screen::GteTest => render_gte_test(&font, &mut gpu, gte_frame, gte_model, gte_yaw, gte_auto, gte_rate, gte_x, gte_y, gte_z),''',
'''            Screen::GteTest => render_gte_test(&font, &mut gpu, gte_frame, gte_model, gte_yaw, gte_auto, gte_rate, gte_x, gte_y, gte_z, gte_cam_x, gte_cam_z),''',
"render call",
)

start = s.find('fn render_play11_floor(gpu: &mut Gpu) {')
end = s.find('fn render_play11_mesh(', start)
if start < 0 or end < 0:
    raise SystemExit('3d_play12_runtime_patch: floor block not found')
new_floor = r'''fn render_play12_floor(gpu: &mut Gpu, cam_x: i32, cam_z: i32) {
    scene::set_screen_offset(160 << 16, 112 << 16);
    scene::set_projection_plane(220);
    scene::load_rotation(&Mat3I16::rotate_y(0));
    scene::load_translation(Vec3I32::new(0, 0, 0x3A00));

    // Infinite scrolling floor: only the modulo phase follows the camera,
    // so the local coordinates always stay safely inside i16 range.
    let phase_x = (cam_x % 3000) as i16;
    let phase_z = (cam_z % 3000) as i16;

    let mut zi = 0i16;
    while zi < 12 {
        let z = -9000 + zi * 3000 - phase_z;
        let a = scene::project_vertex(Vec3I16::new(-15000, 3200, z));
        let b = scene::project_vertex(Vec3I16::new( 15000, 3200, z));
        let bright = 92u8.saturating_sub((zi as u8) * 5);
        gpu.draw(&LineMono::new(a.sx, a.sy, b.sx, b.sy, bright / 3, bright, bright));
        zi += 1;
    }

    let mut xi = 0i16;
    while xi < 11 {
        let x = -15000 + xi * 3000 - phase_x;
        let a = scene::project_vertex(Vec3I16::new(x, 3200, -9000));
        let b = scene::project_vertex(Vec3I16::new(x, 3200, 21000));
        gpu.draw(&LineMono::new(a.sx, a.sy, b.sx, b.sy, 30, 54, 62));
        xi += 1;
    }

    // Two brighter rails make a readable corridor/runway through the world.
    for rail_x in [-7200i16, 7200i16] {
        let a = scene::project_vertex(Vec3I16::new(rail_x - phase_x, 3050, -9000));
        let b = scene::project_vertex(Vec3I16::new(rail_x - phase_x, 3050, 21000));
        gpu.draw(&LineMono::new(a.sx, a.sy, b.sx, b.sy, 94, 138, 150));
    }

    // Repeating side pylons: tiny vertical references amplify speed and depth.
    let mut p = 0i16;
    while p < 8 {
        let z = -6000 + p * 4200 - ((cam_z % 4200) as i16);
        for x in [-9000i16, 9000i16] {
            let base = scene::project_vertex(Vec3I16::new(x - phase_x, 3200, z));
            let top  = scene::project_vertex(Vec3I16::new(x - phase_x, 1200, z));
            gpu.draw(&LineMono::new(base.sx, base.sy, top.sx, top.sy, 112, 76, 140));
        }
        p += 1;
    }
}

'''
s = s[:start] + new_floor + s[end:]

rep(
'''    world_z: i32,
) {''',
'''    world_z: i32,
) {''',
"mesh signature guard",
)

rep(
'''    render_play11_floor(gpu);

    if model == 0 {''',
'''    render_play12_floor(gpu, cam_x, cam_z);

    let view_x = world_x - cam_x;
    let view_z = world_z - cam_z;

    if model == 0 {''',
"floor call",
)

rep(
'''            frame, yaw, world_x, world_y, world_z,
        );''',
'''            frame, yaw, view_x, world_y, view_z,
        );''',
"ufo camera transform",
)
rep(
'''            frame, yaw, world_x, world_y, world_z,
        );''',
'''            frame, yaw, view_x, world_y, view_z,
        );''',
"zurg camera transform",
)

rep(
'''    world_z: i32,
) {
    render_play12_floor(gpu, cam_x, cam_z);''',
'''    world_z: i32,
    cam_x: i32,
    cam_z: i32,
) {
    render_play12_floor(gpu, cam_x, cam_z);''',
"render signature",
)

rep('''    font.draw_text(8, 6, "3D PLAY 1.1 / TEXTURED", (0x70, 0xD0, 0xD0));''',
    '''    font.draw_text(8, 6, "3D PLAY 1.2 / FLIGHT", (0x70, 0xD0, 0xD0));''',
    "title")
rep('''    font.draw_text(8, 174, "D-PAD = X / DEPTH    TRI/X = HEIGHT", (0x68, 0x68, 0x70));
    font.draw_text(8, 190, "L1/R1 = TURN   SQUARE = RATE", (0x68, 0x68, 0x70));''',
    '''    font.draw_text(8, 174, "D-PAD = THRUST    TRI/X = LIFT", (0x68, 0x68, 0x70));
    font.draw_text(8, 190, "INERTIA + FOLLOW CAM   SQUARE = RATE", (0x68, 0x68, 0x70));''',
    "hud")

p.write_text(s)
print('3d_play12_runtime_patch: installed inertia, follow camera and runway floor')
