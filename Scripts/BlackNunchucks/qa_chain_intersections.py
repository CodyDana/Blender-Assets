import bpy
import json
import argparse
import sys
import os
import hashlib
from itertools import combinations
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
os.environ.setdefault('PIPELINE_LOCK_DIR',str(ROOT/'WorkFiles/locks'))
sys.path.insert(0,str(ROOT/'Scripts/pipeline'))
from lock import assert_owner
assert_owner('BlackNunchucks','codex')


parser=argparse.ArgumentParser()
parser.add_argument('--lod',type=int,default=0)
parser.add_argument('--all-pairs',action='store_true')
parser.add_argument('--out',default=str(ROOT/'WorkFiles/BlackNunchucks/chain_intersection_qa.json'))
args=parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
OUT=Path(args.out)
depsgraph = bpy.context.evaluated_depsgraph_get()

def geometry(part):
    matches = [o for o in bpy.data.objects if o.type == 'MESH' and o.get('part_id') == part and o.get('lod_level') == args.lod]
    if len(matches) != 1:
        raise RuntimeError(f'Expected one LOD0 part {part}; found {[o.name for o in matches]}')
    ob = matches[0]
    ev = ob.evaluated_get(depsgraph)
    me = ev.to_mesh()
    me.calc_loop_triangles()
    verts = [ev.matrix_world @ v.co for v in me.vertices]
    triangles = [tuple(t.vertices) for t in me.loop_triangles]
    tree = BVHTree.FromPolygons(verts, triangles, all_triangles=True, epsilon=0.0)
    ev.to_mesh_clear()
    sectors=(14,10,8)[args.lod]
    count=(len(verts)-(2 if part.startswith('eye_') else 0))//sectors
    centers=np.array([[sum(verts[j*sectors+k][ax] for k in range(sectors))/sectors for ax in range(3)] for j in range(count)])
    radius=max((verts[k]-Vector(centers[0])).length for k in range(sectors))
    return {'name': ob.name, 'verts': verts, 'triangles': triangles, 'tree': tree, 'centers':centers,'radius':radius}

def triangle_intersects(a, b, tol=1e-10):
    # Separating-axis verification after BVH candidate generation. Edge cross
    # products plus both face normals cover noncoplanar pairs; in-plane edge
    # normals also handle coplanar triangles. Degenerate axes are ignored.
    ae = [a[(i+1)%3]-a[i] for i in range(3)]
    be = [b[(i+1)%3]-b[i] for i in range(3)]
    na, nb = ae[0].cross(ae[1]), be[0].cross(be[1])
    axes = [na, nb]
    axes.extend(e.cross(f) for e in ae for f in be)
    axes.extend(na.cross(e) for e in ae)
    axes.extend(nb.cross(e) for e in be)
    for axis in axes:
        if axis.length_squared < 1e-28:
            continue
        axis.normalize()
        av = [axis.dot(p) for p in a]
        bv = [axis.dot(p) for p in b]
        if max(av) < min(bv)-tol or max(bv) < min(av)-tol:
            return False
    return True

parts = [f'chain_{i:02d}' for i in range(1,8)] + ['eye_L', 'eye_R']
geo = {part: geometry(part) for part in parts}
intended_pairs = [(f'chain_{i:02d}', f'chain_{i+1:02d}') for i in range(1,7)] + [('eye_L','chain_01'), ('eye_R','chain_07')]
pairs=list(combinations(parts,2)) if args.all_pairs else intended_pairs
results = []
for pa,pb in pairs:
    a,b=geo[pa],geo[pb]
    candidates=a['tree'].overlap(b['tree'])
    actual=[]
    points=[]
    for ia,ib in candidates:
        ta=[a['verts'][vi] for vi in a['triangles'][ia]]
        tb=[b['verts'][vi] for vi in b['triangles'][ib]]
        if triangle_intersects(ta,tb):
            actual.append([ia,ib]); points.extend(ta+tb)
    bounds = None
    if points:
        bounds = {'min': [min(p[k] for p in points) for k in range(3)], 'max': [max(p[k] for p in points) for k in range(3)]}
    item={'parts':[pa,pb], 'objects':[a['name'],b['name']], 'bvh_overlap_pair_count':len(candidates), 'verified_triangle_intersection_pairs':len(actual), 'unique_triangles_A':len(set(i for i,j in actual)), 'unique_triangles_B':len(set(j for i,j in actual)), 'intersecting_triangle_bounds_m':bounds, 'triangle_pairs':actual}
    results.append(item)
    print('CHAIN_QA', pa, pb, 'BVH',len(candidates),'SAT verified',len(actual),flush=True)

def dense_centers(p,subdivisions=6):
    return np.array([p[i]*(1-f/subdivisions)+p[(i+1)%len(p)]*(f/subdivisions) for i in range(len(p)) for f in range(subdivisions)])

def polyline_distance(p,q):
    # Exact shortest distance between every pair of straight centerline segments.
    u=(np.roll(p,-1,axis=0)-p)[:,None,:]
    v=(np.roll(q,-1,axis=0)-q)[None,:,:]
    w=p[:,None,:]-q[None,:,:]
    a=np.sum(u*u,axis=2);b=np.sum(u*v,axis=2);c=np.sum(v*v,axis=2)
    d=np.sum(u*w,axis=2);e=np.sum(v*w,axis=2);den=a*c-b*b
    good=abs(den)>1e-24
    safe=np.where(good,den,1)
    ss=(b*e-c*d)/safe;tt=(a*e-b*d)/safe
    internal=np.sum((w+ss[:,:,None]*u-tt[:,:,None]*v)**2,axis=2)
    internal=np.where(good&(ss>=0)&(ss<=1)&(tt>=0)&(tt<=1),internal,np.inf)
    values=[internal]
    for offset in (0,1):
        ww=w+offset*u;t=np.clip(np.sum(ww*v,axis=2)/c,0,1)
        values.append(np.sum((ww-t[:,:,None]*v)**2,axis=2))
        ww=w-offset*v;s=np.clip(-np.sum(ww*u,axis=2)/a,0,1)
        values.append(np.sum((ww+s[:,:,None]*u)**2,axis=2))
    return float(np.sqrt(np.min(values)))

linking=[]
for pa,pb in intended_pairs:
    p=dense_centers(geo[pa]['centers']);q=dense_centers(geo[pb]['centers'])
    dp=np.roll(p,-1,axis=0)-p;dq=np.roll(q,-1,axis=0)-q
    r=(p+dp/2)[:,None,:]-(q+dq/2)[None,:,:]
    value=float(np.sum(np.sum(np.cross(dp[:,None,:],dq[None,:,:])*r,axis=2)/np.linalg.norm(r,axis=2)**3)/(4*np.pi))
    separation=polyline_distance(geo[pa]['centers'],geo[pb]['centers'])-geo[pa]['radius']-geo[pb]['radius']
    linking.append({'parts':[pa,pb],'gauss_linking_integral':value,'nearest_integer':round(value),'interlocked':abs(round(value))==1 and abs(abs(value)-1)<.01,'polyline_tube_clearance_m':separation})
    print('LINKING_QA',pa,pb,value,flush=True)

report={'blend':bpy.data.filepath,'blend_sha256':hashlib.sha256(Path(bpy.data.filepath).read_bytes()).hexdigest(),'lod':args.lod,'pair_count':len(pairs), 'method':f'Evaluated LOD{args.lod} world-space triangles; BVHTree overlap at epsilon 0, independently verified with triangle separating-axis test at tolerance 1e-10 m. Weld rings, caps and intentional embedded eye anchors excluded by part selection. Linking uses midpoint quadrature of Gauss integral with each centerline edge subdivided six times; open eyes close across their cap-embedded bases.', 'file_was_saved':False, 'pairs':results, 'total_verified_triangle_intersection_pairs':sum(r['verified_triangle_intersection_pairs'] for r in results),'intended_pair_linking':linking,'all_intended_pairs_interlocked':all(v['interlocked'] for v in linking)}
OUT.write_text(json.dumps(report,indent=2),encoding='utf-8')
print('CHAIN_QA_REPORT',str(OUT),flush=True)
