#!/usr/bin/env python3
from pathlib import Path
import sys
p=Path(sys.argv[1]); s=p.read_text()
old="    render_play2_city(gpu,cam_x,cam_z);"
new="    render_play2_city(gpu,cam_x,cam_z);\n    render_play21_hangar(gpu,cam_x,cam_z);"
if old not in s: raise SystemExit('3d_play21_hangar_patch: render hook not found')
s=s.replace(old,new,1)
s=s.replace("3D PLAY 2 / MANHATTAN CORNER","3D PLAY 2.1 / CITY + HANGAR",1)
s=s.replace("1541 TRI / 1 TPAGE / FOLLOW CAM","CITY 1541 + HANGAR 112 TRI",1)
s += r'''

// 3D PLAY 2.1 - Colony Wars Vengeance Hangar landmark.

const PLAY21_HANGAR_VERTS: [Vec3I16; 72] = [
    Vec3I16::new(3397, 0, 4364),
    Vec3I16::new(3799, 0, 5059),
    Vec3I16::new(5003, 0, 4364),
    Vec3I16::new(4601, 0, 5059),
    Vec3I16::new(2795, 0, 541),
    Vec3I16::new(1591, 0, 1236),
    Vec3I16::new(1993, 0, 1931),
    Vec3I16::new(1993, 0, 541),
    Vec3I16::new(6809, 0, 1236),
    Vec3I16::new(6407, 0, 541),
    Vec3I16::new(6407, 0, 1931),
    Vec3I16::new(5605, 0, 541),
    Vec3I16::new(3197, -281, 1236),
    Vec3I16::new(2795, -281, 1931),
    Vec3I16::new(3799, -281, 3669),
    Vec3I16::new(4601, -281, 3669),
    Vec3I16::new(5605, -281, 1931),
    Vec3I16::new(5203, -281, 1236),
    Vec3I16::new(4601, 0, 3669),
    Vec3I16::new(5605, 0, 1931),
    Vec3I16::new(2795, 0, 1931),
    Vec3I16::new(3799, 0, 3669),
    Vec3I16::new(5203, 0, 1236),
    Vec3I16::new(3197, 0, 1236),
    Vec3I16::new(3475, -351, 3109),
    Vec3I16::new(3119, -351, 2491),
    Vec3I16::new(3475, 0, 3109),
    Vec3I16::new(3119, 0, 2491),
    Vec3I16::new(5281, -351, 2491),
    Vec3I16::new(4925, -351, 3109),
    Vec3I16::new(5281, 0, 2491),
    Vec3I16::new(4925, 0, 3109),
    Vec3I16::new(3844, -351, 1236),
    Vec3I16::new(4556, -351, 1236),
    Vec3I16::new(3844, 0, 1236),
    Vec3I16::new(4556, 0, 1236),
    Vec3I16::new(5261, 0, 3189),
    Vec3I16::new(5519, 0, 2742),
    Vec3I16::new(5519, -145, 2742),
    Vec3I16::new(5261, -145, 3189),
    Vec3I16::new(3942, 0, 905),
    Vec3I16::new(3942, -145, 905),
    Vec3I16::new(4458, -145, 905),
    Vec3I16::new(4458, 0, 905),
    Vec3I16::new(3139, -145, 3189),
    Vec3I16::new(3139, 0, 3189),
    Vec3I16::new(2881, 0, 2742),
    Vec3I16::new(2881, -145, 2742),
    Vec3I16::new(3397, -610, 2279),
    Vec3I16::new(3799, -610, 1583),
    Vec3I16::new(3799, -610, 2974),
    Vec3I16::new(4601, -610, 2974),
    Vec3I16::new(5003, -610, 2279),
    Vec3I16::new(4601, -610, 1583),
    Vec3I16::new(3999, -504, 4712),
    Vec3I16::new(4401, -504, 4712),
    Vec3I16::new(4601, -504, 4364),
    Vec3I16::new(4401, -504, 4016),
    Vec3I16::new(3999, -504, 4016),
    Vec3I16::new(3799, -504, 4364),
    Vec3I16::new(2193, -504, 1584),
    Vec3I16::new(2595, -504, 1584),
    Vec3I16::new(2795, -504, 1236),
    Vec3I16::new(2595, -504, 888),
    Vec3I16::new(2193, -504, 888),
    Vec3I16::new(1993, -504, 1236),
    Vec3I16::new(6207, -504, 888),
    Vec3I16::new(5805, -504, 888),
    Vec3I16::new(5605, -504, 1236),
    Vec3I16::new(5805, -504, 1584),
    Vec3I16::new(6207, -504, 1584),
    Vec3I16::new(6407, -504, 1236),
];
const PLAY21_HANGAR_TRIS: [(u16,u16,u16,u8); 112] = [
    (29,51,15,0),(25,48,13,0),(2,18,15,1),(14,21,0,1),(57,2,15,1),(56,2,57,1),(59,14,0,1),(58,14,59,1),(61,6,13,1),(60,6,61,1),(33,53,17,0),(63,12,4,1),(62,12,63,1),(70,16,10,1),(69,16,70,1),(12,23,4,1),(6,20,13,1),(16,19,10,1),(11,22,17,1),(68,11,17,1),(67,11,68,1),(52,28,16,0),(50,24,14,0),(49,32,12,0),(12,13,48,2),(12,48,49,2),(47,44,24,3),(47,24,25,3),(51,50,14,2),(51,14,15,2),(16,17,53,2),(16,53,52,2),(18,31,29,4),(18,29,15,4),(20,27,25,4),(20,25,13,4),(52,53,49,1),(52,49,48,1),(64,63,4,1),(64,4,7,1),(54,59,0,1),(54,0,1,1),(56,55,3,1),(56,3,2,1),(67,66,9,1),(67,9,11,1),(15,14,58,1),(15,58,57,1),(55,54,1,1),(55,1,3,1),(22,35,33,4),(22,33,17,4),(46,47,25,1),(46,25,27,1),(65,64,7,1),(65,7,5,1),(60,65,5,1),(60,5,6,1),(62,61,13,1),(62,13,12,1),(44,45,26,1),(44,26,24,1),(69,68,17,1),(69,17,16,1),(66,71,8,1),(66,8,9,1),(71,70,10,1),(71,10,8,1),(43,42,33,1),(43,33,35,1),(57,58,55,1),(57,55,56,1),(42,41,32,3),(42,32,33,3),(41,40,34,1),(41,34,32,1),(39,38,28,3),(39,28,29,3),(36,39,29,1),(36,29,31,1),(38,37,30,1),(38,30,28,1),(63,64,61,1),(63,61,62,1),(36,37,38,4),(36,38,39,4),(29,28,52,0),(29,52,51,0),(16,28,30,4),(16,30,19,4),(46,45,44,4),(46,44,47,4),(25,24,50,0),(25,50,48,0),(14,24,26,4),(14,26,21,4),(41,42,43,4),(41,43,40,4),(49,53,33,0),(49,33,32,0),(12,32,34,4),(12,34,23,4),(54,55,58,1),(54,58,59,1),(60,61,64,1),(60,64,65,1),(68,69,66,1),(68,66,67,1),(71,66,69,1),(71,69,70,1),(50,51,52,1),(50,52,48,1),
];

fn render_play21_hangar(gpu: &mut Gpu, cam_x: i32, cam_z: i32) {
    scene::set_screen_offset(160 << 16, 112 << 16);
    scene::set_projection_plane(220);
    scene::load_rotation(&Mat3I16::rotate_y(0));
    scene::load_translation(Vec3I32::new(-cam_x, 2600, -cam_z));
    let mut projected=[scene::Projected::default();72];
    let mut vi=0usize;
    while vi<PLAY21_HANGAR_VERTS.len() { projected[vi]=scene::project_vertex(PLAY21_HANGAR_VERTS[vi]); vi+=1; }
    let mut head=[-1i16;256];
    let mut next=[-1i16;112];
    let mut ti=0usize;
    while ti<PLAY21_HANGAR_TRIS.len() {
        let (a,b,c,_m)=PLAY21_HANGAR_TRIS[ti];
        let pa=projected[a as usize]; let pb=projected[b as usize]; let pc=projected[c as usize];
        let avg=((pa.sz as u32+pb.sz as u32+pc.sz as u32)/3) as u16;
        let mut bucket=(avg>>6) as usize; if bucket>255 { bucket=255; }
        next[ti]=head[bucket]; head[bucket]=ti as i16; ti+=1;
    }
    let mut bucket=255i16;
    while bucket>=0 {
        let mut cur=head[bucket as usize];
        while cur>=0 {
            let i=cur as usize;
            let (a,b,c,m)=PLAY21_HANGAR_TRIS[i];
            let pa=projected[a as usize]; let pb=projected[b as usize]; let pc=projected[c as usize];
            if pa.sx>-1000 && pa.sx<1000 && pa.sy>-800 && pa.sy<800 && pb.sx>-1000 && pb.sx<1000 && pb.sy>-800 && pb.sy<800 && pc.sx>-1000 && pc.sx<1000 && pc.sy>-800 && pc.sy<800 {
                let d=((255-bucket as u8)>>3) as u8;
                let (r,g,bcol)=match m {
                    0 => (58u8.saturating_add(d),72u8.saturating_add(d),88u8.saturating_add(d)),
                    1 => (76u8.saturating_add(d),70u8.saturating_add(d),62u8.saturating_add(d)),
                    2 => (46u8.saturating_add(d),64u8.saturating_add(d),78u8.saturating_add(d)),
                    3 => (88u8.saturating_add(d),58u8.saturating_add(d),40u8.saturating_add(d)),
                    _ => (52u8.saturating_add(d),78u8.saturating_add(d),62u8.saturating_add(d)),
                };
                gpu.draw(&TriFlat::new([(pa.sx,pa.sy),(pb.sx,pb.sy),(pc.sx,pc.sy)],r,g,bcol));
            }
            cur=next[i];
        }
        bucket-=1;
    }
}
'''
p.write_text(s)
print('3d_play21_hangar_patch: installed 72-vertex / 112-triangle Hangar landmark')
