#!/usr/bin/env python3
from pathlib import Path
import sys

p=Path(sys.argv[1]); s=p.read_text()

def rep(old,new,label):
    global s
    if old not in s:
        raise SystemExit(f'3d_play14: {label} pattern not found')
    s=s.replace(old,new,1)

# Add POV camera state. Keep the validated 1.3b state untouched otherwise.
rep(
'''    let mut gte_scale_q12: i32 = 4096;''',
'''    let mut gte_scale_q12: i32 = 4096;
    // 3D PLAY 1.4: the camera is now the moving entity.
    let mut pov_x: i32 = 0;
    let mut pov_y: i32 = 0;
    let mut pov_z: i32 = -1000;
    let mut pov_yaw: u16 = 0;''',
'pov state')

# Upload both compact character textures when entering 3D mode. HOME VRAM is reused while 3D is active.
rep(
'''                        3 => { gte_frame = 0; Screen::GteTest },''',
'''                        3 => {
                            gte_frame = 0;
                            upload_play14_world_textures();
                            pov_x = 0; pov_y = 0; pov_z = -1000; pov_yaw = 0;
                            Screen::GteTest
                        },''',
'enter GTE')

# Replace the whole validated movement block with camera movement. Objects remain fixed in world space.
start = s.find('                    let accel = match gte_rate {')
end_anchor = '                    let turn = (gte_rate as u16) * 10;'
end = s.find(end_anchor, start)
if start < 0 or end < 0:
    raise SystemExit('3d_play14: runtime controls block not found')
# Include old turn/scale block through its closing braces, up to the end of the GteTest else branch.
end2 = s.find('                }\n            }', end)
if end2 < 0:
    raise SystemExit('3d_play14: controls end not found')
new_controls = r'''                    let accel = match gte_rate { 1=>18i32, 2=>28i32, 3=>44i32, 4=>66i32, _=>96i32 };
                    let vmax  = match gte_rate { 1=>120i32, 2=>200i32, 3=>320i32, 4=>460i32, _=>640i32 };

                    // Camera yaw. One full revolution = 256 units.
                    let turn = (gte_rate as u16) * 2;
                    if held(bits, button::L1) { pov_yaw = pov_yaw.wrapping_sub(turn); }
                    if held(bits, button::R1) { pov_yaw = pov_yaw.wrapping_add(turn); }

                    // Camera-local movement vectors transformed into world space.
                    let cam_rot = Mat3I16::rotate_y(pov_yaw);
                    let mut move_x = 0i32;
                    let mut move_z = 0i32;
                    if held(bits, button::UP)    { move_z += accel; }
                    if held(bits, button::DOWN)  { move_z -= accel; }
                    if held(bits, button::RIGHT) { move_x += accel; }
                    if held(bits, button::LEFT)  { move_x -= accel; }
                    let mv = cam_rot.transform_i32([move_x, 0, move_z]);
                    pov_x += mv[0];
                    pov_z += mv[2];

                    if held(bits, button::TRIANGLE) { pov_y -= accel; }
                    if held(bits, button::CROSS)    { pov_y += accel; }

                    // Keep the camera inside a generous border around the 8x8 board.
                    pov_x = pov_x.clamp(-15000, 15000);
                    pov_z = pov_z.clamp(-15000, 15000);
                    pov_y = pov_y.clamp(-6500, 4500);

                    // SELECT recenters the POV. START keeps its old auto-rotation state but no longer moves objects.
                    if just_pressed(pressed, button::SELECT) {
                        pov_x = 0; pov_y = 0; pov_z = -1000; pov_yaw = 0;
                    }
                    if just_pressed(pressed, button::L2) { gte_scale_q12 = 4096; }
                    if held(bits, button::R2) {
                        let ss = match gte_rate { 1=>32i32, 2=>48i32, 3=>72i32, 4=>104i32, _=>144i32 };
                        if held(bits, button::L1) { gte_scale_q12 = (gte_scale_q12 - ss).max(1024); }
                        if held(bits, button::R1) { gte_scale_q12 = (gte_scale_q12 + ss).min(12288); }
                    }
'''
s = s[:start] + new_controls + s[end2:]

# On exit restore HOME artwork because we reuse its VRAM page for Tyrant/T-Rex.
rep(
'''                if just_pressed(pressed, button::CIRCLE) {
                    screen = Screen::TestMenu;
                } else {''',
'''                if just_pressed(pressed, button::CIRCLE) {
                    upload_home_image();
                    screen = Screen::TestMenu;
                } else {''',
'GTE exit restore')

# Replace render call with POV renderer.
rep(
'''            Screen::GteTest => render_gte_test(&font, &mut gpu, gte_frame, gte_model, gte_yaw, gte_auto, gte_rate, gte_x, gte_y, gte_z, gte_cam_x, gte_cam_z, gte_scale_q12),''',
'''            Screen::GteTest => render_play14_world(&font, &mut gpu, gte_frame, gte_rate, pov_x, pov_y, pov_z, pov_yaw, gte_scale_q12),''',
'render call')

# Insert the world renderer before the old render_gte_test. The old renderer remains available but unused.
idx=s.find('fn render_gte_test(\n')
if idx<0: raise SystemExit('3d_play14: render_gte_test anchor not found')
helper=r'''
const PLAY14_BOARD_HALF: i32 = 12000;
const PLAY14_TILE: i32 = 3000;
const PLAY14_GROUND_Y: i32 = 3200;
const PLAY14_EXTRA_TPAGE: TexturePage = TexturePage::new(832, 256, TextureDepth::Bit8);
const PLAY14_TYRANT_CLUT: Clut = Clut::new(512, 496);
const PLAY14_TREX_CLUT: Clut = Clut::new(768, 496);

fn upload_play14_world_textures() {
    const PX: usize = 64*64;
    // Tyrant at U=0..63, T-Rex at U=64..127 inside HOME's left 8bpp page.
    let a = VramRect::new(PLAY14_EXTRA_TPAGE.x(), PLAY14_EXTRA_TPAGE.y(), 32, 64);
    upload_bytes(a, &PLAY13B_TYRANT_TEX[..PX]);
    let b = VramRect::new(PLAY14_EXTRA_TPAGE.x()+32, PLAY14_EXTRA_TPAGE.y(), 32, 64);
    upload_bytes(b, &PLAY13B_TREX_TEX[..PX]);
    let ca = VramRect::new(PLAY14_TYRANT_CLUT.x(), PLAY14_TYRANT_CLUT.y(), 256, 1);
    upload_bytes(ca, &PLAY13B_TYRANT_TEX[PX..]);
    let cb = VramRect::new(PLAY14_TREX_CLUT.x(), PLAY14_TREX_CLUT.y(), 256, 1);
    upload_bytes(cb, &PLAY13B_TREX_TEX[PX..]);
}

#[inline(always)]
fn play14_camera_space(wx:i32, wy:i32, wz:i32, cx:i32, cy:i32, cz:i32, yaw:u16) -> [i32;3] {
    let inv = Mat3I16::rotate_y((0u16).wrapping_sub(yaw));
    inv.transform_i32([wx-cx, wy-cy, wz-cz])
}

fn render_play14_floor(gpu:&mut Gpu, cx:i32, cy:i32, cz:i32, yaw:u16) {
    scene::set_screen_offset(160<<16,112<<16);
    scene::set_projection_plane(220);
    scene::load_rotation(&Mat3I16::IDENTITY);
    scene::load_translation(Vec3I32::ZERO);

    // 8x8 board proportions: 9 lines each axis, not a literal chess texture.
    let mut i=0i32;
    while i<=8 {
        let x=-PLAY14_BOARD_HALF + i*PLAY14_TILE;
        let a=play14_camera_space(x,PLAY14_GROUND_Y,-PLAY14_BOARD_HALF,cx,cy,cz,yaw);
        let b=play14_camera_space(x,PLAY14_GROUND_Y, PLAY14_BOARD_HALF,cx,cy,cz,yaw);
        if a[2]>128 && b[2]>128 && a[0].abs()<32000 && a[1].abs()<32000 && a[2]<32000 && b[0].abs()<32000 && b[1].abs()<32000 && b[2]<32000 {
            let pa=scene::project_vertex(Vec3I16::new(a[0] as i16,a[1] as i16,a[2] as i16));
            let pb=scene::project_vertex(Vec3I16::new(b[0] as i16,b[1] as i16,b[2] as i16));
            gpu.draw(&LineMono::new(pa.sx,pa.sy,pb.sx,pb.sy,44,72,78));
        }
        i+=1;
    }
    let mut j=0i32;
    while j<=8 {
        let z=-PLAY14_BOARD_HALF + j*PLAY14_TILE;
        let a=play14_camera_space(-PLAY14_BOARD_HALF,PLAY14_GROUND_Y,z,cx,cy,cz,yaw);
        let b=play14_camera_space( PLAY14_BOARD_HALF,PLAY14_GROUND_Y,z,cx,cy,cz,yaw);
        if a[2]>128 && b[2]>128 && a[0].abs()<32000 && a[1].abs()<32000 && a[2]<32000 && b[0].abs()<32000 && b[1].abs()<32000 && b[2]<32000 {
            let pa=scene::project_vertex(Vec3I16::new(a[0] as i16,a[1] as i16,a[2] as i16));
            let pb=scene::project_vertex(Vec3I16::new(b[0] as i16,b[1] as i16,b[2] as i16));
            gpu.draw(&LineMono::new(pa.sx,pa.sy,pb.sx,pb.sy,44,72,78));
        }
        j+=1;
    }
}

fn draw_play14_extra_tri(verts:[(i16,i16);3], uvs:[(u8,u8);3], uoff:u8, clut:Clut) {
    let add = |u:u8| -> u8 { u.saturating_add(uoff) };
    wait_command_ready();
    write_command(psx_hw::gpu::packet::FLAT_TEXTURED_TRIANGLE | pack_color(0x80,0x80,0x80));
    write_command(pack_vertex(verts[0].0,verts[0].1));
    write_command(pack_texcoord(add(uvs[0].0),uvs[0].1,clut.uv_word()));
    write_command(pack_vertex(verts[1].0,verts[1].1));
    write_command(pack_texcoord(add(uvs[1].0),uvs[1].1,PLAY14_EXTRA_TPAGE.uv_word(0)));
    write_command(pack_vertex(verts[2].0,verts[2].1));
    write_command(pack_texcoord(add(uvs[2].0),uvs[2].1,0));
}

fn render_play14_extra_at(
    verts:&[Vec3I16], faces:&[(u16,u16,u16)], face_uvs:&[[(u8,u8);3]],
    world_x:i32, world_y:i32, world_z:i32,
    cam_x:i32, cam_y:i32, cam_z:i32, cam_yaw:u16,
    uoff:u8, clut:Clut, scale_q12:i32,
) {
    let t=play14_camera_space(world_x,world_y,world_z,cam_x,cam_y,cam_z,cam_yaw);
    if t[2] < 256 || t[2] > 30000 { return; }
    scene::set_screen_offset(160<<16,112<<16); scene::set_projection_plane(220);
    scene::load_translation(Vec3I32::new(t[0],t[1],t[2]));
    let inv=Mat3I16::rotate_y((0u16).wrapping_sub(cam_yaw));
    let pitch=Mat3I16::rotate_x(96);
    let scaled=inv.mul(&pitch).scale_columns_q12([scale_q12,scale_q12,scale_q12]);
    scene::load_rotation(&scaled);
    let mut fi=0usize;
    while fi<faces.len() {
        let(a,b,c)=faces[fi];
        let pa=scene::project_vertex(verts[a as usize]);
        let pb=scene::project_vertex(verts[b as usize]);
        let pc=scene::project_vertex(verts[c as usize]);
        if pa.sz>64&&pb.sz>64&&pc.sz>64&&pa.sx>-900&&pa.sx<900&&pa.sy>-700&&pa.sy<700&&pb.sx>-900&&pb.sx<900&&pb.sy>-700&&pb.sy<700&&pc.sx>-900&&pc.sx<900&&pc.sy>-700&&pc.sy<700 {
            draw_play14_extra_tri([(pa.sx,pa.sy),(pb.sx,pb.sy),(pc.sx,pc.sy)],face_uvs[fi],uoff,clut);
        }
        fi+=1;
    }
}

fn render_play14_mesh_at(
    gpu:&mut Gpu, verts:&[Vec3I16], faces:&[(u16,u16,u16)], uvs:&[[(u8,u8);3]],
    tpage:TexturePage, clut:Clut,
    world_x:i32,world_y:i32,world_z:i32,
    cam_x:i32,cam_y:i32,cam_z:i32,cam_yaw:u16, scale_q12:i32,
) {
    let t=play14_camera_space(world_x,world_y,world_z,cam_x,cam_y,cam_z,cam_yaw);
    if t[2] < 256 || t[2] > 30000 { return; }
    scene::set_screen_offset(160<<16,112<<16); scene::set_projection_plane(220);
    scene::load_translation(Vec3I32::new(t[0],t[1],t[2]));
    let inv=Mat3I16::rotate_y((0u16).wrapping_sub(cam_yaw));
    let pitch=Mat3I16::rotate_x(96);
    let scaled=inv.mul(&pitch).scale_columns_q12([scale_q12,scale_q12,scale_q12]);
    scene::load_rotation(&scaled);

    let mut projected=[scene::Projected::default(); PLAY13B_MAX_VERTS];
    let mut vi=0usize; while vi<verts.len(){projected[vi]=scene::project_vertex(verts[vi]);vi+=1;}
    let mut head=[-1i16;256]; let mut next=[-1i16;PLAY13B_MAX_FACES];
    let mut fi=0usize; while fi<faces.len(){let(a,b,c)=faces[fi];let pa=projected[a as usize];let pb=projected[b as usize];let pc=projected[c as usize];let avg=((pa.sz as u32+pb.sz as u32+pc.sz as u32)/3)as u16;let mut bucket=(avg>>6)as usize;if bucket>255{bucket=255;}next[fi]=head[bucket];head[bucket]=fi as i16;fi+=1;}
    let mut bucket=255i16; while bucket>=0 {let mut cur=head[bucket as usize];while cur>=0{let i=cur as usize;let(a,b,c)=faces[i];let pa=projected[a as usize];let pb=projected[b as usize];let pc=projected[c as usize];if pa.sx>-900&&pa.sx<900&&pa.sy>-700&&pa.sy<700&&pb.sx>-900&&pb.sx<900&&pb.sy>-700&&pb.sy<700&&pc.sx>-900&&pc.sx<900&&pc.sy>-700&&pc.sy<700{draw_play11_textured_tri([(pa.sx,pa.sy),(pb.sx,pb.sy),(pc.sx,pc.sy)],uvs[i],tpage,clut);}cur=next[i];}bucket-=1;}
    let _=gpu;
}

fn render_play14_world(font:&FontAtlas,gpu:&mut Gpu,frame:u16,rate:u8,cx:i32,cy:i32,cz:i32,cam_yaw:u16,scale_q12:i32) {
    render_play14_floor(gpu,cx,cy,cz,cam_yaw);

    // Four fixed corner pieces on the 8x8 board. Camera starts near the center.
    let q=9000i32;
    render_play14_mesh_at(gpu,&UFO_VERTS,&UFO_FACES,&UFO_UVS,PLAY11_UFO_TPAGE,PLAY11_UFO_CLUT,-q,0,-q,cx,cy,cz,cam_yaw,scale_q12);
    render_play14_mesh_at(gpu,&ZURG_VERTS,&ZURG_FACES,&ZURG_UVS,PLAY11_ZURG_TPAGE,PLAY11_ZURG_CLUT, q,0,-q,cx,cy,cz,cam_yaw,scale_q12);
    render_play14_extra_at(&TYRANT_VERTS,&TYRANT_FACES,&TYRANT_UVS,-q,0,q,cx,cy,cz,cam_yaw,0,PLAY14_TYRANT_CLUT,scale_q12);
    render_play14_extra_at(&TREX_VERTS,&TREX_FACES,&TREX_UVS, q,0,q,cx,cy,cz,cam_yaw,64,PLAY14_TREX_CLUT,scale_q12);

    font.draw_text(8,6,"3D PLAY 1.4 / POV WORLD",(0x70,0xD0,0xD0));
    font.draw_text(8,22,"8x8 SCALE / 4 CORNER PIECES",(0x58,0x90,0x90));
    const RATE_LABELS:[&str;5]=["RATE 1","RATE 2","RATE 3","RATE 4","RATE 5"];
    font.draw_text(250,6,RATE_LABELS[(rate.saturating_sub(1).min(4)) as usize],(0xA0,0xA0,0x70));
    font.draw_text(8,174,"D-PAD=MOVE CAMERA   TRI/X=HEIGHT",(0x68,0x68,0x70));
    font.draw_text(8,190,"L1/R1=LOOK LEFT/RIGHT   SQUARE=RATE",(0x68,0x68,0x70));
    font.draw_text(8,206,"SELECT=CENTER   R2+L1/R1=SCALE",(0x68,0x68,0x70));
    font.draw_text(8,222,"CIRCLE=BACK",(0x58,0x58,0x60));
    let _=frame;
}

'''
s=s[:idx]+helper+s[idx:]

p.write_text(s)
print('3d_play14: POV camera + 8x8 board + four fixed corner models')
