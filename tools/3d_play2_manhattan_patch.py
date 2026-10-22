#!/usr/bin/env python3
from pathlib import Path
import sys
p=Path(sys.argv[1]); s=p.read_text()

def rep(old,new,label):
    global s
    if old not in s:
        raise SystemExit(f'3d_play2_manhattan_patch: {label} pattern not found')
    s=s.replace(old,new,1)

rep(
    'use psx_gpu::prim::LineMono;\nmod mesh3d;',
    'use psx_gpu::prim::{LineMono, TriFlat};\nmod mesh3d;\nmod manhattan;\nuse manhattan::{MANHATTAN_VERTS, MANHATTAN_TRIS};',
    'imports')

rep(
    'const PLAY11_ZURG_CLUT: Clut = Clut::new(512, 497);',
    '''const PLAY11_ZURG_CLUT: Clut = Clut::new(512, 497);

// 3D PLAY 2: two compacted 256x256 8-bit atlases made from the 41 source materials.
// They intentionally reuse the two PLAY1 texture pages; PLAY2 renders UFO/Zurg flat-shaded.
static PLAY2_ATLAS0: &[u8] = include_bytes!("manhattan_atlas0.bin");
static PLAY2_ATLAS1: &[u8] = include_bytes!("manhattan_atlas1.bin");
const PLAY2_TEX_PIXELS: usize = 256 * 256;
const PLAY2_TPAGE0: TexturePage = TexturePage::new(768, 0, TextureDepth::Bit8);
const PLAY2_TPAGE1: TexturePage = TexturePage::new(896, 0, TextureDepth::Bit8);
const PLAY2_CLUT0: Clut = Clut::new(256, 497);
const PLAY2_CLUT1: Clut = Clut::new(512, 497);''',
    'constants')

rep(
    '    upload_prisma_image();\n    upload_play11_textures();',
    '    upload_prisma_image();\n    upload_play11_textures();\n    upload_play2_textures();',
    'texture upload call')

rep('    let mut gte_z: i32 = 0x3600;', '    let mut gte_z: i32 = 0;', 'initial z')
rep('    let mut gte_cam_z: i32 = 0;', '    let mut gte_cam_z: i32 = -0x3600;', 'initial camera z')

rep(
'''                    if gte_x < -18000 { gte_x = -18000; gte_vx = 0; }
                    if gte_x >  18000 { gte_x =  18000; gte_vx = 0; }
                    if gte_y <  -6200 { gte_y =  -6200; gte_vy = 0; }
                    if gte_y >   6200 { gte_y =   6200; gte_vy = 0; }
                    if gte_z <   0x1800 { gte_z = 0x1800; gte_vz = 0; }
                    if gte_z >   0xB000 { gte_z = 0xB000; gte_vz = 0; }''',
'''                    // Keep the marker inside the extracted Manhattan corner.
                    if gte_x < -7200 { gte_x = -7200; gte_vx = 0; }
                    if gte_x >  7200 { gte_x =  7200; gte_vx = 0; }
                    if gte_y < -2200 { gte_y = -2200; gte_vy = 0; }
                    if gte_y >  2400 { gte_y =  2400; gte_vy = 0; }
                    if gte_z < -4800 { gte_z = -4800; gte_vz = 0; }
                    if gte_z >  4800 { gte_z =  4800; gte_vz = 0; }''',
    'world bounds')

idx=s.find('fn render_gte_test(\n')
if idx<0:
    raise SystemExit('3d_play2_manhattan_patch: render_gte_test not found')
s=s[:idx] + r'''const PLAY2_MAX_VERTS: usize = 906;
const PLAY2_MAX_TRIS: usize = 1541;

fn upload_play2_textures() {
    let r0 = VramRect::new(PLAY2_TPAGE0.x(), PLAY2_TPAGE0.y(), 128, 256);
    upload_bytes(r0, &PLAY2_ATLAS0[..PLAY2_TEX_PIXELS]);
    let c0 = VramRect::new(PLAY2_CLUT0.x(), PLAY2_CLUT0.y(), 256, 1);
    upload_bytes(c0, &PLAY2_ATLAS0[PLAY2_TEX_PIXELS..]);
    let r1 = VramRect::new(PLAY2_TPAGE1.x(), PLAY2_TPAGE1.y(), 128, 256);
    upload_bytes(r1, &PLAY2_ATLAS1[..PLAY2_TEX_PIXELS]);
    let c1 = VramRect::new(PLAY2_CLUT1.x(), PLAY2_CLUT1.y(), 256, 1);
    upload_bytes(c1, &PLAY2_ATLAS1[PLAY2_TEX_PIXELS..]);
}

fn render_play2_city(gpu: &mut Gpu, cam_x: i32, cam_z: i32) {
    scene::set_screen_offset(160 << 16, 112 << 16);
    scene::set_projection_plane(220);
    scene::load_rotation(&Mat3I16::rotate_y(0));
    scene::load_translation(Vec3I32::new(-cam_x, 2600, -cam_z));
    let mut projected = [scene::Projected::default(); PLAY2_MAX_VERTS];
    let mut vi=0usize;
    while vi<MANHATTAN_VERTS.len() { projected[vi]=scene::project_vertex(MANHATTAN_VERTS[vi]); vi+=1; }
    let mut head=[-1i16;256];
    let mut next=[-1i16;PLAY2_MAX_TRIS];
    let mut ti=0usize;
    while ti<MANHATTAN_TRIS.len() {
        let t=MANHATTAN_TRIS[ti];
        let pa=projected[t.idx.0 as usize]; let pb=projected[t.idx.1 as usize]; let pc=projected[t.idx.2 as usize];
        let avg=((pa.sz as u32 + pb.sz as u32 + pc.sz as u32)/3) as u16;
        let mut bucket=(avg>>6) as usize; if bucket>255 { bucket=255; }
        next[ti]=head[bucket]; head[bucket]=ti as i16; ti+=1;
    }
    let mut bucket=255i16;
    while bucket>=0 {
        let mut cur=head[bucket as usize];
        while cur>=0 {
            let i=cur as usize; let t=MANHATTAN_TRIS[i];
            let pa=projected[t.idx.0 as usize]; let pb=projected[t.idx.1 as usize]; let pc=projected[t.idx.2 as usize];
            if pa.sx>-1000 && pa.sx<1000 && pa.sy>-800 && pa.sy<800 && pb.sx>-1000 && pb.sx<1000 && pb.sy>-800 && pb.sy<800 && pc.sx>-1000 && pc.sx<1000 && pc.sy>-800 && pc.sy<800 {
                if t.page==0 {
                    draw_play11_textured_tri([(pa.sx,pa.sy),(pb.sx,pb.sy),(pc.sx,pc.sy)],t.uv,PLAY2_TPAGE0,PLAY2_CLUT0);
                } else if t.page==1 {
                    draw_play11_textured_tri([(pa.sx,pa.sy),(pb.sx,pb.sy),(pc.sx,pc.sy)],t.uv,PLAY2_TPAGE1,PLAY2_CLUT1);
                } else {
                    let shade=72u8.saturating_add(((255-bucket as u8)>>3) as u8);
                    gpu.draw(&TriFlat::new([(pa.sx,pa.sy),(pb.sx,pb.sy),(pc.sx,pc.sy)],shade,shade,shade.saturating_add(8)));
                }
            }
            cur=next[i];
        }
        bucket-=1;
    }
}

fn render_play2_marker(gpu: &mut Gpu, verts: &[Vec3I16], faces: &[(u16,u16,u16)], model: u8, frame: u16, yaw_manual: u16, view_x: i32, world_y: i32, view_z: i32) {
    scene::set_screen_offset(160 << 16,112 << 16);
    scene::set_projection_plane(220);
    scene::load_translation(Vec3I32::new(view_x,2600+world_y,view_z));
    let yaw=Mat3I16::rotate_y(yaw_manual.wrapping_add(frame.wrapping_mul(4)));
    let pitch=Mat3I16::rotate_x(96);
    scene::load_rotation(&yaw.mul(&pitch));
    let mut projected=[scene::Projected::default();PLAY11_MAX_VERTS];
    let mut vi=0usize; while vi<verts.len() { projected[vi]=scene::project_vertex(verts[vi]); vi+=1; }
    let mut head=[-1i16;256]; let mut next=[-1i16;PLAY11_MAX_FACES];
    let mut fi=0usize;
    while fi<faces.len() {
        let (a,b,c)=faces[fi]; let pa=projected[a as usize]; let pb=projected[b as usize]; let pc=projected[c as usize];
        let avg=((pa.sz as u32+pb.sz as u32+pc.sz as u32)/3) as u16; let mut bucket=(avg>>6) as usize; if bucket>255 { bucket=255; }
        next[fi]=head[bucket]; head[bucket]=fi as i16; fi+=1;
    }
    let mut bucket=255i16;
    while bucket>=0 {
        let mut cur=head[bucket as usize];
        while cur>=0 {
            let i=cur as usize; let (a,b,c)=faces[i]; let pa=projected[a as usize]; let pb=projected[b as usize]; let pc=projected[c as usize];
            if pa.sx>-900 && pa.sx<900 && pa.sy>-700 && pa.sy<700 && pb.sx>-900 && pb.sx<900 && pb.sy>-700 && pb.sy<700 && pc.sx>-900 && pc.sx<900 && pc.sy>-700 && pc.sy<700 {
                let shade=86u8.saturating_add(((255-bucket as u8)>>3) as u8);
                let (r,g,bcol)=if model==0 {(shade/2,shade.saturating_add(60),shade.saturating_add(80))} else {(shade.saturating_add(80),shade/2,shade.saturating_add(22))};
                gpu.draw(&TriFlat::new([(pa.sx,pa.sy),(pb.sx,pb.sy),(pc.sx,pc.sy)],r,g,bcol));
            }
            cur=next[i];
        }
        bucket-=1;
    }
}

fn render_gte_test(font: &FontAtlas, gpu: &mut Gpu, frame: u16, model: u8, yaw: u16, auto_rotate: bool, rate: u8, world_x: i32, world_y: i32, world_z: i32, cam_x: i32, cam_z: i32) {
    render_play2_city(gpu,cam_x,cam_z);
    let view_x=world_x-cam_x; let view_z=world_z-cam_z;
    if model==0 { render_play2_marker(gpu,&UFO_VERTS,&UFO_FACES,model,frame,yaw,view_x,world_y,view_z); }
    else { render_play2_marker(gpu,&ZURG_VERTS,&ZURG_FACES,model,frame,yaw,view_x,world_y,view_z); }
    font.draw_text(8,6,"3D PLAY 2 / MANHATTAN CORNER",(0x70,0xD0,0xD0));
    font.draw_text(8,22,"1541 TRI / 2 TPAGE / FOLLOW CAM",(0x68,0x88,0x88));
    const RATE_LABELS:[&str;5]=["RATE 1","RATE 2","RATE 3","RATE 4","RATE 5"];
    font.draw_text(250,6,RATE_LABELS[(rate.saturating_sub(1).min(4)) as usize],(0xA0,0xA0,0x70));
    font.draw_text(8,174,"D-PAD = MOVE    TRI/X = HEIGHT",(0x68,0x68,0x70));
    font.draw_text(8,190,"L1/R1 = TURN   SQUARE = RATE",(0x68,0x68,0x70));
    font.draw_text(8,206,"SELECT = UFO/ZURG MARKER",(0x68,0x68,0x70));
    if auto_rotate { font.draw_text(190,206,"START=AUTO OFF",(0x60,0xA0,0x70)); } else { font.draw_text(190,206,"START=AUTO ON",(0xA0,0x80,0x60)); }
    font.draw_text(8,222,"CIRCLE = BACK",(0x58,0x58,0x60));
}
'''

p.write_text(s)
print('3d_play2_manhattan_patch: installed Manhattan Corner scene')
