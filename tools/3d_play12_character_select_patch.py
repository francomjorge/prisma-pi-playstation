#!/usr/bin/env python3
from pathlib import Path
import sys
p=Path(sys.argv[1]); s=p.read_text()

def rep(old,new,label):
    global s
    if old not in s:
        raise SystemExit(f'character_select_patch: {label} not found')
    s=s.replace(old,new,1)

rep(
    'use psx_gpu::prim::LineMono;\nmod mesh3d;\nuse mesh3d::{UFO_VERTS, UFO_FACES, UFO_UVS, ZURG_VERTS, ZURG_FACES, ZURG_UVS};',
    'use psx_gpu::prim::{LineMono, TriFlat};\nmod mesh3d;\nmod extra_chars;\nuse mesh3d::{UFO_VERTS, UFO_FACES, UFO_UVS, ZURG_VERTS, ZURG_FACES, ZURG_UVS};\nuse extra_chars::{TYRANT_VERTS, TYRANT_FACES, TREX_VERTS, TREX_FACES};',
    'imports')

rep(
    'if just_pressed(pressed, button::SELECT) { gte_model ^= 1; }',
    'if just_pressed(pressed, button::SELECT) { gte_model = if gte_model >= 3 { 0 } else { gte_model + 1 }; }',
    'select cycle')

marker='fn render_gte_test(\n'
pos=s.find(marker)
if pos<0: raise SystemExit('character_select_patch: render_gte_test not found')
extra=r'''fn render_extra_character(
    gpu: &mut Gpu,
    verts: &[Vec3I16],
    faces: &[(u16,u16,u16)],
    frame: u16,
    yaw_manual: u16,
    world_x: i32,
    world_y: i32,
    world_z: i32,
    palette: u8,
) {
    scene::set_screen_offset(160 << 16,112 << 16);
    scene::set_projection_plane(220);
    scene::load_translation(Vec3I32::new(world_x,world_y,world_z));
    let yaw=Mat3I16::rotate_y(yaw_manual.wrapping_add(frame.wrapping_mul(4)));
    let pitch=Mat3I16::rotate_x(96);
    scene::load_rotation(&yaw.mul(&pitch));

    // Deliberately simple for the new characters: no new texture pages, no large
    // temporary projection buffers, and no changes to the validated 1.2 path.
    let mut i=0usize;
    while i<faces.len() {
        let (a,b,c)=faces[i];
        let pa=scene::project_vertex(verts[a as usize]);
        let pb=scene::project_vertex(verts[b as usize]);
        let pc=scene::project_vertex(verts[c as usize]);
        if pa.sz>64 && pb.sz>64 && pc.sz>64 &&
           pa.sx>-900 && pa.sx<900 && pa.sy>-700 && pa.sy<700 &&
           pb.sx>-900 && pb.sx<900 && pb.sy>-700 && pb.sy<700 &&
           pc.sx>-900 && pc.sx<900 && pc.sy>-700 && pc.sy<700 {
            let avg=((pa.sz as u32+pb.sz as u32+pc.sz as u32)/3) as u16;
            let shade=70u8.saturating_add(((0x3fff_u16.saturating_sub(avg))>>8).min(55) as u8);
            let (r,g,bcol)=if palette==0 {
                (shade.saturating_add(55),shade,shade)
            } else {
                (shade,shade.saturating_add(28),shade/2)
            };
            gpu.draw(&TriFlat::new([(pa.sx,pa.sy),(pb.sx,pb.sy),(pc.sx,pc.sy)],r,g,bcol));
        }
        i+=1;
    }
}

'''
s=s[:pos]+extra+s[pos:]

old='''    if model == 0 {
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
    }'''
new='''    match model {
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
        2 => render_extra_character(gpu,&TYRANT_VERTS,&TYRANT_FACES,frame,yaw,view_x,world_y,view_z,0),
        _ => render_extra_character(gpu,&TREX_VERTS,&TREX_FACES,frame,yaw,view_x,world_y,view_z,1),
    }'''
rep(old,new,'render model match')

oldhud='''    if model == 0 {
        font.draw_text(8, 22, "ALIEN MOTHERSHIP / 753 TRI", (0x58, 0x90, 0x90));
    } else {
        font.draw_text(8, 22, "FLOATING ZURG / 891 TRI", (0x90, 0x58, 0x80));
    }'''
newhud='''    match model {
        0 => font.draw_text(8,22,"ALIEN MOTHERSHIP / 753 TRI",(0x58,0x90,0x90)),
        1 => font.draw_text(8,22,"FLOATING ZURG / 891 TRI",(0x90,0x58,0x80)),
        2 => font.draw_text(8,22,"TYRANT T-103 / REDUCED",(0x98,0x60,0x60)),
        _ => font.draw_text(8,22,"T-REX / REDUCED",(0x70,0x98,0x60)),
    }'''
rep(oldhud,newhud,'hud model label')
rep('font.draw_text(8, 206, "SELECT = MODEL", (0x68, 0x68, 0x70));','font.draw_text(8, 206, "SELECT = UFO / ZURG / TYRANT / T-REX", (0x68, 0x68, 0x70));','hud select')

p.write_text(s)
print('character_select_patch: stable 1.2 + 4-model SELECT installed')
