#!/usr/bin/env python3
from pathlib import Path
import sys
p=Path(sys.argv[1]); s=p.read_text()
def rep(old,new,label):
    global s
    if old not in s: raise SystemExit(f'3d_play13: {label} pattern not found')
    s=s.replace(old,new,1)

rep(
'use extra_chars::{TYRANT_VERTS, TYRANT_FACES, TREX_VERTS, TREX_FACES};',
'use extra_chars::{TYRANT_VERTS, TYRANT_FACES, TREX_VERTS, TREX_FACES};\nmod extra_uvs;\nuse extra_uvs::{TYRANT_UVS, TREX_UVS};',
'uv imports')

rep(
'const PLAY11_ZURG_CLUT: Clut = Clut::new(512, 497);',
'''const PLAY11_ZURG_CLUT: Clut = Clut::new(512, 497);
static PLAY13_TYRANT_TEX: &[u8] = include_bytes!("play13_tyrant_tex.bin");
static PLAY13_TREX_TEX: &[u8] = include_bytes!("play13_trex_tex.bin");''',
'texture statics')

rep(
'''    let mut gte_cam_x: i32 = 0;
    let mut gte_cam_z: i32 = 0;''',
'''    let mut gte_cam_x: i32 = 0;
    let mut gte_cam_z: i32 = 0;
    let mut gte_inspect_pitch: i16 = 96;
    let mut gte_scale_q12: i32 = 4096;
    let mut gte_inspect_zoom: i32 = 0;''',
'inspect state')

rep(
'if just_pressed(pressed, button::SELECT) { gte_model = (gte_model + 1) & 3; }',
'''if just_pressed(pressed, button::SELECT) {
                        gte_model = (gte_model + 1) & 3;
                        upload_play13_model_texture(gte_model);
                    }
                    if just_pressed(pressed, button::L2) {
                        gte_inspect_pitch = 96;
                        gte_scale_q12 = 4096;
                        gte_inspect_zoom = 0;
                    }''',
'select/reset')

old='''                    let accel = match gte_rate {
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
new='''                    let accel = match gte_rate { 1=>6i32, 2=>11i32, 3=>18i32, 4=>28i32, _=>42i32 };
                    let vmax = match gte_rate { 1=>90i32, 2=>150i32, 3=>230i32, 4=>330i32, _=>470i32 };
                    let turn = (gte_rate as u16) * 10;
                    let inspect = held(bits, button::R2);
                    if inspect {
                        gte_vx=0; gte_vy=0; gte_vz=0;
                        if held(bits, button::LEFT)  { gte_yaw = gte_yaw.wrapping_sub(turn); }
                        if held(bits, button::RIGHT) { gte_yaw = gte_yaw.wrapping_add(turn); }
                        let tilt=(gte_rate as i16)*2;
                        if held(bits, button::UP)   { gte_inspect_pitch=(gte_inspect_pitch-tilt).max(24); }
                        if held(bits, button::DOWN) { gte_inspect_pitch=(gte_inspect_pitch+tilt).min(168); }
                        let zoom_step=match gte_rate {1=>64,2=>96,3=>144,4=>208,_=>288};
                        if held(bits, button::TRIANGLE) { gte_inspect_zoom=(gte_inspect_zoom-zoom_step).max(-10500); }
                        if held(bits, button::CROSS)    { gte_inspect_zoom=(gte_inspect_zoom+zoom_step).min(15000); }
                        let scale_step=match gte_rate {1=>48,2=>72,3=>104,4=>144,_=>208};
                        if held(bits, button::L1) { gte_scale_q12=(gte_scale_q12-scale_step).max(1536); }
                        if held(bits, button::R1) { gte_scale_q12=(gte_scale_q12+scale_step).min(10240); }
                    } else {
                        let lr = held(bits, button::LEFT) || held(bits, button::RIGHT);
                        let fb = held(bits, button::UP) || held(bits, button::DOWN);
                        let ud = held(bits, button::TRIANGLE) || held(bits, button::CROSS);
                        if held(bits, button::LEFT)  { gte_vx -= accel; if gte_vx < -vmax { gte_vx = -vmax; } }
                        if held(bits, button::RIGHT) { gte_vx += accel; if gte_vx >  vmax { gte_vx =  vmax; } }
                        if held(bits, button::UP)    { gte_vz += accel; if gte_vz >  vmax { gte_vz =  vmax; } }
                        if held(bits, button::DOWN)  { gte_vz -= accel; if gte_vz < -vmax { gte_vz = -vmax; } }
                        if held(bits, button::TRIANGLE) { gte_vy -= accel; if gte_vy < -vmax { gte_vy = -vmax; } }
                        if held(bits, button::CROSS)    { gte_vy += accel; if gte_vy >  vmax { gte_vy =  vmax; } }
                        if !lr { gte_vx=(gte_vx*7)/8; }
                        if !fb { gte_vz=(gte_vz*7)/8; }
                        if !ud { gte_vy=(gte_vy*7)/8; }
                        gte_x += gte_vx; gte_y += gte_vy; gte_z += gte_vz;
                        if held(bits, button::L1) { gte_yaw = gte_yaw.wrapping_sub(turn); }
                        if held(bits, button::R1) { gte_yaw = gte_yaw.wrapping_add(turn); }
                    }
                    if gte_x < -18000 { gte_x=-18000; gte_vx=0; }
                    if gte_x >  18000 { gte_x= 18000; gte_vx=0; }
                    if gte_y <  -6200 { gte_y=-6200; gte_vy=0; }
                    if gte_y >   6200 { gte_y= 6200; gte_vy=0; }
                    if gte_z < 0x1800 { gte_z=0x1800; gte_vz=0; }
                    if gte_z > 0xB000 { gte_z=0xB000; gte_vz=0; }
                    gte_cam_x += (gte_x-gte_cam_x)/7;
                    let cam_z_target=gte_z-0x3600;
                    gte_cam_z += (cam_z_target-gte_cam_z)/9;'''
rep(old,new,'controls')

rep(
'''            Screen::GteTest => render_gte_test(&font, &mut gpu, gte_frame, gte_model, gte_yaw, gte_auto, gte_rate, gte_x, gte_y, gte_z, gte_cam_x, gte_cam_z),''',
'''            Screen::GteTest => render_gte_test(&font, &mut gpu, gte_frame, gte_model, gte_yaw, gte_auto, gte_rate, gte_x, gte_y, gte_z, gte_cam_x, gte_cam_z, gte_inspect_pitch, gte_scale_q12, gte_inspect_zoom),''',
'render call')

idx=s.find('fn render_gte_test(\n')
if idx<0: raise SystemExit('3d_play13: render_gte_test not found')
helper=r'''fn upload_play13_page(data: &[u8]) {
    let r=VramRect::new(PLAY11_UFO_TPAGE.x(),PLAY11_UFO_TPAGE.y(),128,256);
    upload_bytes(r,&data[..PLAY11_TEX_PIXELS]);
    let c=VramRect::new(PLAY11_UFO_CLUT.x(),PLAY11_UFO_CLUT.y(),256,1);
    upload_bytes(c,&data[PLAY11_TEX_PIXELS..]);
}
fn upload_play13_model_texture(model:u8) {
    match model { 0=>upload_play13_page(PLAY11_UFO_TEX), 2=>upload_play13_page(PLAY13_TYRANT_TEX), 3=>upload_play13_page(PLAY13_TREX_TEX), _=>{} }
}

const PLAY13_MAX_VERTS:usize=917;
const PLAY13_MAX_FACES:usize=1718;
fn render_play13_mesh(
    gpu:&mut Gpu, verts:&[Vec3I16], faces:&[(u16,u16,u16)], face_uvs:&[[(u8,u8);3]],
    tpage:TexturePage, clut:Clut, frame:u16, yaw_manual:u16, pitch_angle:i16, scale_q12:i32,
    world_x:i32, world_y:i32, world_z:i32,
) {
    scene::set_screen_offset(160<<16,112<<16); scene::set_projection_plane(220);
    scene::load_translation(Vec3I32::new(world_x,world_y,world_z));
    let yaw=Mat3I16::rotate_y(yaw_manual.wrapping_add(frame.wrapping_mul(4)));
    let pitch=Mat3I16::rotate_x(pitch_angle as u16);
    let rot=yaw.mul(&pitch).scale_columns_q12([scale_q12,scale_q12,scale_q12]);
    scene::load_rotation(&rot);
    let mut projected=[scene::Projected::default();PLAY13_MAX_VERTS];
    let mut vi=0usize; while vi<verts.len(){projected[vi]=scene::project_vertex(verts[vi]);vi+=1;}
    let mut head=[-1i16;256]; let mut next=[-1i16;PLAY13_MAX_FACES];
    let mut fi=0usize; while fi<faces.len(){let(a,b,c)=faces[fi];let pa=projected[a as usize];let pb=projected[b as usize];let pc=projected[c as usize];let avg=((pa.sz as u32+pb.sz as u32+pc.sz as u32)/3)as u16;let mut bucket=(avg>>6)as usize;if bucket>255{bucket=255;}next[fi]=head[bucket];head[bucket]=fi as i16;fi+=1;}
    let mut bucket=255i16; while bucket>=0 {let mut cur=head[bucket as usize];while cur>=0{let i=cur as usize;let(a,b,c)=faces[i];let pa=projected[a as usize];let pb=projected[b as usize];let pc=projected[c as usize];if pa.sx>-900&&pa.sx<900&&pa.sy>-700&&pa.sy<700&&pb.sx>-900&&pb.sx<900&&pb.sy>-700&&pb.sy<700&&pc.sx>-900&&pc.sx<900&&pc.sy>-700&&pc.sy<700{draw_play11_textured_tri([(pa.sx,pa.sy),(pb.sx,pb.sy),(pc.sx,pc.sy)],face_uvs[i],tpage,clut);}cur=next[i];}bucket-=1;}
}

'''
s=s[:idx]+helper+s[idx:]

rep(
'''    cam_x: i32,
    cam_z: i32,
) {''',
'''    cam_x: i32,
    cam_z: i32,
    inspect_pitch: i16,
    scale_q12: i32,
    inspect_zoom: i32,
) {''',
'render signature')

old_switch='''    match model {
        0 => render_play11_mesh(
            gpu, &UFO_VERTS, &UFO_FACES, &UFO_UVS,
            PLAY11_UFO_TPAGE, PLAY11_UFO_CLUT,
            frame, yaw, view_x, world_y, view_z,
        ),
        1 => render_play11_mesh(
            gpu, &ZURG_VERTS, &ZURG_FACES, &ZURG_UVS,
            PLAY11_ZURG_TPAGE, PLAY11_ZURG_CLUT,
            frame, yaw, view_x, world_y, view_z,
        ),
        2 => render_extra_character(
            gpu, &TYRANT_VERTS, &TYRANT_FACES,
            frame, yaw, view_x, world_y, view_z, 0,
        ),
        _ => render_extra_character(
            gpu, &TREX_VERTS, &TREX_FACES,
            frame, yaw, view_x, world_y, view_z, 1,
        ),
    }'''
new_switch='''    let inspect_z=view_z+inspect_zoom;
    match model {
        0 => render_play13_mesh(gpu,&UFO_VERTS,&UFO_FACES,&UFO_UVS,PLAY11_UFO_TPAGE,PLAY11_UFO_CLUT,frame,yaw,inspect_pitch,scale_q12,view_x,world_y,inspect_z),
        1 => render_play13_mesh(gpu,&ZURG_VERTS,&ZURG_FACES,&ZURG_UVS,PLAY11_ZURG_TPAGE,PLAY11_ZURG_CLUT,frame,yaw,inspect_pitch,scale_q12,view_x,world_y,inspect_z),
        2 => render_play13_mesh(gpu,&TYRANT_VERTS,&TYRANT_FACES,&TYRANT_UVS,PLAY11_UFO_TPAGE,PLAY11_UFO_CLUT,frame,yaw,inspect_pitch,scale_q12,view_x,world_y,inspect_z),
        _ => render_play13_mesh(gpu,&TREX_VERTS,&TREX_FACES,&TREX_UVS,PLAY11_UFO_TPAGE,PLAY11_UFO_CLUT,frame,yaw,inspect_pitch,scale_q12,view_x,world_y,inspect_z),
    }'''
rep(old_switch,new_switch,'render switch')

rep('font.draw_text(8, 190, "INERTIA + FOLLOW CAM   SQUARE = RATE", (0x68, 0x68, 0x70));',
    'font.draw_text(8, 190, "HOLD R2: PAD=ORBIT  TRI/X=ZOOM", (0x68, 0x68, 0x70));','hud inspect')
rep('font.draw_text(8, 206, "SELECT = NEXT MODEL", (0x68, 0x68, 0x70));',
    'font.draw_text(8, 206, "R2+L1/R1=SCALE  L2=RESET  SELECT", (0x68, 0x68, 0x70));','hud select')
s=s.replace('font.draw_text(160, 206, "START = AUTO OFF"','font.draw_text(190, 158, "START=AUTO OFF"',1)
s=s.replace('font.draw_text(160, 206, "START = AUTO ON"','font.draw_text(190, 158, "START=AUTO ON"',1)

p.write_text(s)
print('3d_play13_textures_inspect_patch: textured all 4 + inspect controls')
