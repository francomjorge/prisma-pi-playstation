#!/usr/bin/env python3
from pathlib import Path
import sys
p=Path(sys.argv[1]); s=p.read_text()

def rep(old,new,label):
    global s
    if old not in s:
        raise SystemExit(f'3d_play12_extra_chars_patch: {label} pattern not found')
    s=s.replace(old,new,1)

rep(
'''use psx_gpu::prim::LineMono;
mod mesh3d;
use mesh3d::{UFO_VERTS, UFO_FACES, UFO_UVS, ZURG_VERTS, ZURG_FACES, ZURG_UVS};''',
'''use psx_gpu::prim::{LineMono, TriFlat};
mod mesh3d;
mod extra_chars;
use mesh3d::{UFO_VERTS, UFO_FACES, UFO_UVS, ZURG_VERTS, ZURG_FACES, ZURG_UVS};
use extra_chars::{TYRANT_VERTS, TYRANT_FACES, TREX_VERTS, TREX_FACES};''',
'imports')

rep(
'if just_pressed(pressed, button::SELECT) { gte_model ^= 1; }',
'if just_pressed(pressed, button::SELECT) { gte_model = if gte_model >= 3 { 0 } else { gte_model + 1 }; }',
'select cycle')

insert_at=s.find('fn render_gte_test(\n')
if insert_at<0:
    raise SystemExit('3d_play12_extra_chars_patch: render_gte_test not found')
extra=r'''fn render_play12_extra_flat(
    gpu: &mut Gpu,
    verts: &[Vec3I16],
    faces: &[(u16,u16,u16)],
    frame: u16,
    yaw_manual: u16,
    world_x: i32,
    world_y: i32,
    world_z: i32,
    model: u8,
) {
    scene::set_screen_offset(160 << 16, 112 << 16);
    scene::set_projection_plane(220);
    scene::load_translation(Vec3I32::new(world_x, world_y, world_z));
    let yaw = Mat3I16::rotate_y(yaw_manual.wrapping_add(frame.wrapping_mul(4)));
    let pitch = Mat3I16::rotate_x(96);
    scene::load_rotation(&yaw.mul(&pitch));

    let mut fi=0usize;
    while fi<faces.len() {
        let (a,b,c)=faces[fi];
        let pa=scene::project_vertex(verts[a as usize]);
        let pb=scene::project_vertex(verts[b as usize]);
        let pc=scene::project_vertex(verts[c as usize]);
        if pa.sz>64 && pb.sz>64 && pc.sz>64 &&
           pa.sx>-900 && pa.sx<900 && pa.sy>-700 && pa.sy<700 &&
           pb.sx>-900 && pb.sx<900 && pb.sy>-700 && pb.sy<700 &&
           pc.sx>-900 && pc.sx<900 && pc.sy>-700 && pc.sy<700 {
            let avg=((pa.sz as u32+pb.sz as u32+pc.sz as u32)/3) as u16;
            let shade=74u8.saturating_add(((0x6000u32.saturating_sub(avg as u32))>>9).min(70) as u8);
            let (r,g,bcol)=if model==2 {
                (shade.saturating_add(38), shade/2, shade/2)
            } else {
                (shade/2, shade.saturating_add(32), shade/2)
            };
            gpu.draw(&TriFlat::new([(pa.sx,pa.sy),(pb.sx,pb.sy),(pc.sx,pc.sy)],r,g,bcol));
        }
        fi+=1;
    }
}

'''
s=s[:insert_at]+extra+s[insert_at:]

rep(
'''    if model == 0 {
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
    }''',
'''    if model == 0 {
        render_play11_mesh(
            gpu, &UFO_VERTS, &UFO_FACES, &UFO_UVS,
            PLAY11_UFO_TPAGE, PLAY11_UFO_CLUT,
            frame, yaw, view_x, world_y, view_z,
        );
    } else if model == 1 {
        render_play11_mesh(
            gpu, &ZURG_VERTS, &ZURG_FACES, &ZURG_UVS,
            PLAY11_ZURG_TPAGE, PLAY11_ZURG_CLUT,
            frame, yaw, view_x, world_y, view_z,
        );
    } else if model == 2 {
        render_play12_extra_flat(gpu,&TYRANT_VERTS,&TYRANT_FACES,frame,yaw,view_x,world_y,view_z,model);
    } else {
        render_play12_extra_flat(gpu,&TREX_VERTS,&TREX_FACES,frame,yaw,view_x,world_y,view_z,model);
    }''',
'render selector')

rep(
'''    if model == 0 {
        font.draw_text(8, 22, "ALIEN MOTHERSHIP / 753 TRI", (0x58, 0x90, 0x90));
    } else {
        font.draw_text(8, 22, "FLOATING ZURG / 891 TRI", (0x90, 0x58, 0x80));
    }''',
'''    if model == 0 {
        font.draw_text(8, 22, "ALIEN MOTHERSHIP / 753 TRI", (0x58, 0x90, 0x90));
    } else if model == 1 {
        font.draw_text(8, 22, "FLOATING ZURG / 891 TRI", (0x90, 0x58, 0x80));
    } else if model == 2 {
        font.draw_text(8, 22, "TYRANT T-103 / 1246 TRI", (0x98, 0x58, 0x58));
    } else {
        font.draw_text(8, 22, "T-REX / 1718 TRI", (0x58, 0x98, 0x58));
    }''',
'hud model label')

p.write_text(s)
print('3d_play12_extra_chars_patch: SELECT cycles UFO/Zurg/Tyrant/T-Rex; 1.2 runtime otherwise unchanged')
