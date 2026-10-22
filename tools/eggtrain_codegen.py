#!/usr/bin/env python3
from pathlib import Path
import base64,gzip,struct,sys
src=Path(sys.argv[1]); out=Path(sys.argv[2])
raw=gzip.decompress(base64.b64decode(src.read_text().strip()))
off=0
vcount,tcount=struct.unpack_from('<HH',raw,off); off+=4
verts=[]
for _ in range(vcount):
    verts.append(struct.unpack_from('<hhh',raw,off)); off+=6
tris=[]
for _ in range(tcount):
    a,b,c=struct.unpack_from('<HHH',raw,off); off+=6
    uv=[]
    for _ in range(3):
        u,v=struct.unpack_from('<BB',raw,off); off+=2; uv.append((u,v))
    page=raw[off]; off+=1
    tris.append((a,b,c,uv,page))
if off!=len(raw): raise SystemExit(f'trailing bytes: {len(raw)-off}')
p=[]
p.append('// Auto-generated Egg Train PS1 room\n')
p.append('use psx_gte::math::Vec3I16;\n\n')
p.append('#[derive(Clone, Copy)]\npub struct EggTri {\n    pub idx: (u16,u16,u16),\n    pub uv: [(u8,u8);3],\n}\n\n')
p.append(f'pub const EGGTRAIN_VERTS: [Vec3I16; {vcount}] = [\n')
for x,y,z in verts: p.append(f'    Vec3I16::new({x}, {y}, {z}),\n')
p.append('];\n\n')
p.append(f'pub const EGGTRAIN_TRIS: [EggTri; {tcount}] = [\n')
for a,b,c,uv,page in tris:
    p.append(f'    EggTri {{ idx: ({a},{b},{c}), uv: [({uv[0][0]},{uv[0][1]}),({uv[1][0]},{uv[1][1]}),({uv[2][0]},{uv[2][1]})] }},\n')
p.append('];\n')
out.write_text(''.join(p))
print(f'eggtrain_codegen: {vcount} verts, {tcount} tris -> {out}')
