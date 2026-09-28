import numpy as np
from collections import defaultdict
V=np.load("built_verts.npy"); E=np.load("built_bnd.npy")
adj=defaultdict(list)
for a,b in E: adj[a].append(b); adj[b].append(a)
seen=set(); loops=[]
for s in list(adj):
    if s in seen: continue
    loop=[s]; seen.add(s); cur=s; prev=None
    while True:
        nxt=[n for n in adj[cur] if n!=prev and n not in seen]
        if not nxt:
            if s in adj[cur] and len(loop)>2: pass
            break
        cur2=nxt[0]; loop.append(cur2); seen.add(cur2); prev=cur; cur=cur2
    loops.append(loop)
loops=[l for l in loops if len(l)>3]
for i,l in enumerate(loops):
    pts=V[l][:,:2]
    r=np.hypot(pts[:,0],pts[:,1])
    area=0.5*abs(np.sum(pts[:,0]*np.roll(pts[:,1],-1)-np.roll(pts[:,0],-1)*pts[:,1]))
    print(f"loop {i}: n={len(l)} rmin={r.min()*1000:.2f}mm rmax={r.max()*1000:.2f}mm area={area*1e6:.1f}mm2")
    np.save(f"built_loop{i}.npy", pts)
