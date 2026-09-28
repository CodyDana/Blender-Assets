"""List the PNG chunks of the smoke bomb reference (provenance check). Read-only; writes nothing."""
import struct, hashlib, sys
p = sys.argv[1]
b = open(p, 'rb').read()
print(len(b), hashlib.sha256(b).hexdigest())
i = 8
while i < len(b):
    n = struct.unpack('>I', b[i:i+4])[0]; t = b[i+4:i+8]
    body = b[i+8:i+8+n]
    if t == b'IHDR':
        print(t, n, struct.unpack('>IIBBBBB', body))
    elif t != b'IDAT':
        s = body[:400]
        print(t, n, s)
        if t in (b'caBX', b'iTXt', b'tEXt', b'eXIf'):
            for key in (b'OpenAI', b'openai', b'ChatGPT', b'GPT', b'c2pa', b'trainedAlgorithmicMedia', b'Google', b'Adobe'):
                if key in body: print('   contains', key)
    i += 12 + n
