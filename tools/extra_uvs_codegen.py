#!/usr/bin/env python3
from pathlib import Path
import base64,gzip,struct,sys
src=Path(sys.argv[1]); out=Path(sys.argv[2])
raw=gzip.decompress(base64.b64decode(src.read_text().strip()))
o=0; p=['// Auto-generated extra character UVs (64x64 compact atlases)\n\n']
for name in ('TYRANT','TREX'):
    fcount=struct.unpack_from('<H',raw,o)[0]; o+=2
    p.append(f'pub const {name}_UVS: [[(u8,u8);3]; {fcount}] = [\n')
    for _ in range(fcount):
        v=struct.unpack_from('<BBBBBB',raw,o); o+=6
        p.append(f'    [({v[0]>>2},{v[1]>>2}),({v[2]>>2},{v[3]>>2}),({v[4]>>2},{v[5]>>2})],\n')
    p.append('];\n\n')
if o!=len(raw): raise SystemExit(f'trailing {len(raw)-o}')
out.write_text(''.join(p)); print(f'extra_uvs_codegen: {len(raw)} bytes -> {out}')
