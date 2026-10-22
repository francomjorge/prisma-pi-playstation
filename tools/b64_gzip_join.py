#!/usr/bin/env python3
from pathlib import Path
import base64, gzip, sys

if len(sys.argv) < 3:
    raise SystemExit('usage: b64_gzip_join.py OUT INPUT...')
out = Path(sys.argv[1])
text = ''.join(''.join(Path(p).read_text().split()) for p in sys.argv[2:])
text += '=' * ((-len(text)) % 4)
raw = gzip.decompress(base64.b64decode(text))
out.write_bytes(raw)
print(f'b64_gzip_join: {len(raw)} bytes -> {out}')
