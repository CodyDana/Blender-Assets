# Remove non-essential PNG chunks (eXIf/oFFs/pHYs/text/time) from the blind pairs; each chunk carries its own CRC.
import struct, glob
for f in sorted(glob.glob('C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/blackhat/blind_r2/pair_*.png')):
    b = open(f, 'rb').read(); out = [b[:8]]; i = 8; kept = []
    while i < len(b):
        n = struct.unpack('>I', b[i:i+4])[0]; t = b[i+4:i+8]; ch = b[i:i+12+n]; i += 12+n
        if t in (b'IHDR', b'PLTE', b'IDAT', b'IEND', b'sRGB', b'gAMA', b'cHRM'): out.append(ch); kept.append(t.decode())
    open(f, 'wb').write(b''.join(out))
print('STRIPPED', kept)
