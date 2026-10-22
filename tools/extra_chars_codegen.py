#!/usr/bin/env python3
from pathlib import Path
import base64,gzip,struct,sys
src=Path(sys.argv[1]); out=Path(sys.argv[2])
raw=gzip.decompress(base64.b64decode(src.read_text().strip()))
off=0
parts=['// Auto-generated extra characters for 3D PLAY 1.2\n','use psx_gte::math::Vec3I16;\n\n']
for name in ('TYRANT','TREX'):
    vcount,fcount=struct.unpack_from('<HH',raw,off); off+=4
    verts=[struct.unpack_from('<hhh',raw,off+i*6) for i in range(vcount)]; off+=vcount*6
    faces=[struct.unpack_from('<HHH',raw,off+i*6) for i in range(fcount)]; off+=fcount*6
    parts.append(f'pub const {name}_VERTS: [Vec3I16; {vcount}] = [\n')
    for x,y,z in verts: parts.append(f'    Vec3I16::new({x}, {y}, {z}),\n')
    parts.append('];\n\n')
    parts.append(f'pub const {name}_FACES: [(u16,u16,u16); {fcount}] = [\n')
    for a,b,c in faces: parts.append(f'    ({a},{b},{c}),\n')
    parts.append('];\n\n')
if off!=len(raw): raise SystemExit(f'trailing bytes: {len(raw)-off}')
out.write_text(''.join(parts))
print(f'extra_chars_codegen: wrote {out} ({len(raw)} bytes raw)')
