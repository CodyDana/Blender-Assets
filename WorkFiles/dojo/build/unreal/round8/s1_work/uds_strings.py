import re, sys
data = open(sys.argv[1], 'rb').read()
out = set()
for m in re.finditer(rb'[\x20-\x7e]{4,}', data):
    out.add(m.group().decode('ascii'))
for s in sorted(out):
    print(s)
