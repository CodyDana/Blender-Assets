"""The masters' neutral default textures (final pass, 2026-09-26). Plain Python (zlib + struct), deterministic.

    py -3 Scripts/unreal/materials/default_textures/make_default_textures.py

A master's texture parameters need a default texture of the right kind (the sampler type must match the compression).
Before this pass the defaults were real item maps (the smoke bomb's 4096 Detail16, the four-point star's maps ...),
so migrating or cooking only the hat or the kunai dragged 40+ MiB of another item's textures along. These 8 x 8 maps
live in /Game/NinjaPack/Textures/Default and are the ONLY textures a master references; every instance overrides them.
"""
import struct
import zlib
from pathlib import Path

HERE = Path(__file__).resolve().parent
SIZE = 8


def chunk(tag, data):
    return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)


def png(path, px, bits, ctype):
    """px: one pixel's sample tuple, repeated SIZE x SIZE."""
    fmt = ">" + ("H" if bits == 16 else "B") * len(px)
    row = b"\x00" + struct.pack(fmt, *px) * SIZE
    ihdr = struct.pack(">IIBBBBB", SIZE, SIZE, bits, ctype, 0, 0, 0)
    blob = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", zlib.compress(row * SIZE, 9)) + chunk(b"IEND", b"")
    Path(path).write_bytes(blob)


MAPS = {
    # name: (samples, bits, PNG colour type, what it is)
    "T_NP_Default_BC": ((255, 255, 255, 255), 8, 6, "white base colour (sRGB)"),
    "T_NP_Default_ORM": ((255, 128, 255, 255), 8, 6, "AO 1, roughness 0.5, metallic 1, specular mask 1"),
    "T_NP_Default_N": ((128, 128, 255, 255), 8, 6, "flat tangent-space normal"),
    "T_NP_Default_Detail16": ((32768,), 16, 0, "16-bit linear grey 0.5 (n = 1 with the master's default Bias 0 / Scale 2)"),
    "T_NP_Default_Lettering": ((0,), 8, 0, "black: no lettering"),
    "T_NP_Default_PaperDetail": ((255, 255, 255, 0), 8, 6, "paper weight 1 (sRGB 255), no pooled ink"),
    "T_NP_Default_InkWeights": ((0, 0, 0, 0), 8, 6, "no ink"),
}

if __name__ == "__main__":
    for name, (px, bits, ctype, _) in MAPS.items():
        png(HERE / f"{name}.png", px, bits, ctype)
        print(name, (HERE / f"{name}.png").stat().st_size)
