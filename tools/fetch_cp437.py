#!/usr/bin/env python3
"""Fetch the pinned public-domain IBM CGA/EGA 8x8 CP437 ROM table.

Source is pinned to a specific onyx_font commit. The upstream table declares
itself as the IBM CGA/EGA BIOS CP437 font, 256 glyphs, 8 bytes per glyph,
public domain. This importer extracts only the 2048 byte table and refuses
anything that does not have exactly 256 glyph rows.
"""
from pathlib import Path
import argparse, re, urllib.request

URL = "https://raw.githubusercontent.com/devbrain/onyx_font/b5edcfdd7c3af99244edf7f03d57107575dedc20/src/onyx_font/bios_font_8x8.cc"

p = argparse.ArgumentParser()
p.add_argument("output", type=Path)
a = p.parse_args()
text = urllib.request.urlopen(URL, timeout=30).read().decode("utf-8")
start = text.index("constexpr std::array<std::uint8_t, 2048> k_vga_8x8")
end = text.index("}};", start)
block = text[start:end]
rows = re.findall(r"^\s*((?:0x[0-9A-Fa-f]{2},?\s*){8})//\s*0x[0-9A-Fa-f]{2}", block, re.M)
if len(rows) != 256:
    raise SystemExit(f"expected 256 CP437 glyph rows, got {len(rows)}")
raw = bytes(int(x, 16) for row in rows for x in re.findall(r"0x([0-9A-Fa-f]{2})", row))
if len(raw) != 2048:
    raise SystemExit(f"expected 2048 bytes, got {len(raw)}")
a.output.parent.mkdir(parents=True, exist_ok=True)
a.output.write_bytes(raw)
print(f"CP437 source imported: {a.output} ({len(raw)} bytes)")
