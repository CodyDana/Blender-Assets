import sys, os, numpy as np
sys.path.insert(0, os.path.dirname(__file__)); from bh_lib import *
a = sys.argv[sys.argv.index('--') + 1:]
x0, x1, xs, y0, y1 = map(int, a[:5])
L = lum(load_srgb())
print('     ' + ' '.join(f'{x:4d}' for x in range(x0, x1, xs)))
for y in range(y0, y1):
    print(f'{y:4d} ' + ' '.join(f'{int(L[y, x]*100):4d}' for x in range(x0, x1, xs)))
