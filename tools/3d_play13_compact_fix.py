#!/usr/bin/env python3
from pathlib import Path
import sys
p=Path(sys.argv[1]); s=p.read_text()
old = '''fn upload_play13_page(data: &[u8]) {
    let r=VramRect::new(PLAY11_UFO_TPAGE.x(),PLAY11_UFO_TPAGE.y(),128,256);
    upload_bytes(r,&data[..PLAY11_TEX_PIXELS]);
    let c=VramRect::new(PLAY11_UFO_CLUT.x(),PLAY11_UFO_CLUT.y(),256,1);
    upload_bytes(c,&data[PLAY11_TEX_PIXELS..]);
}'''
new = '''fn upload_play13_page(data: &[u8]) {
    const PLAY13_TEX_PIXELS: usize = 64 * 64;
    // 8bpp 64x64 = 32 VRAM halfwords x 64 rows. Reuses the UFO page origin.
    let r=VramRect::new(PLAY11_UFO_TPAGE.x(),PLAY11_UFO_TPAGE.y(),32,64);
    upload_bytes(r,&data[..PLAY13_TEX_PIXELS]);
    let c=VramRect::new(PLAY11_UFO_CLUT.x(),PLAY11_UFO_CLUT.y(),256,1);
    upload_bytes(c,&data[PLAY13_TEX_PIXELS..]);
}'''
if old not in s:
    raise SystemExit('compact fix: upload_play13_page pattern not found')
s=s.replace(old,new,1)
p.write_text(s)
print('3d_play13_compact_fix: 64x64 texture upload enabled')
