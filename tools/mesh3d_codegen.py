#!/usr/bin/env python3
from pathlib import Path
import base64,gzip,struct,sys
src=Path(sys.argv[1]); out=Path(sys.argv[2])
raw=gzip.decompress(base64.b64decode(src.read_text().strip()))
off=0
parts=['// Auto-generated 3D PLAY 1.1 mesh + UV data\n','use psx_gte::math::Vec3I16;\n\n']
for name in ('UFO','ZURG'):
    vcount,fcount=struct.unpack_from('<HH',raw,off); off+=4
    verts=[struct.unpack_from('<hhh',raw,off+i*6) for i in range(vcount)]; off+=vcount*6
    faces=[struct.unpack_from('<HHH',raw,off+i*6) for i in range(fcount)]; off+=fcount*6
    uvtris=[]
    for i in range(fcount):
        vals=struct.unpack_from('<BBBBBB',raw,off); off+=6
        uvtris.append(((vals[0],vals[1]),(vals[2],vals[3]),(vals[4],vals[5])))
    parts.append(f'pub const {name}_VERTS: [Vec3I16; {vcount}] = [\n')
    for x,y,z in verts: parts.append(f'    Vec3I16::new({x}, {y}, {z}),\n')
    parts.append('];\n\n')
    parts.append(f'pub const {name}_FACES: [(u16,u16,u16); {fcount}] = [\n')
    for a,b,c in faces: parts.append(f'    ({a},{b},{c}),\n')
    parts.append('];\n\n')
    parts.append(f'pub const {name}_UVS: [[(u8,u8);3]; {fcount}] = [\n')
    for tri in uvtris:
        parts.append(f'    [({tri[0][0]},{tri[0][1]}),({tri[1][0]},{tri[1][1]}),({tri[2][0]},{tri[2][1]})],\n')
    parts.append('];\n\n')
if off!=len(raw): raise SystemExit(f'trailing {len(raw)-off}')
out.write_text(''.join(parts))
print(f'wrote {out} {len(raw)} bytes')
