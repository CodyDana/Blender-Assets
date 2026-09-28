"""Independent, read-only checks for nunchucks runtime recolor preparation.

Run with Blender --background --factory-startup --python this_file.py.
Reads original/current blend files and PNG data. Writes only a QA JSON report.
"""
from pathlib import Path
import bpy, numpy as np, hashlib, json, struct, zlib, zipfile

ROOT=Path(__file__).resolve().parents[2]
WORK=ROOT/'WorkFiles/BlackNunchucks'
BASELINE=ROOT/'Backups/BlackNunchucks_PreRecolor/BlackNunchucks.blend'
CURRENT=ROOT/'Assets/BlackNunchucks.blend'
PARAMS=ROOT/'Exports/BlackNunchucks/recolor_parameters.json'
TEX=ROOT/'Textures/BlackNunchucks'
RND=ROOT/'Renders/BlackNunchucks'

def digest(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def array_hash(a): return hashlib.sha256(np.asarray(a).tobytes()).hexdigest()
def data_hash(a): return hashlib.sha256(json.dumps(a,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def attr_array(collection, attribute, width, dtype):
    a=np.empty(len(collection)*width,dtype=dtype);collection.foreach_get(attribute,a)
    return a.reshape(len(collection),width)

def capture(path, include_uv_samples=False):
    bpy.ops.wm.open_mainfile(filepath=str(path))
    records={}; samples={}
    for ob in sorted(bpy.data.collections['BLACK_NUNCHUCKS'].objects,key=lambda o:o.name):
        r={'type':ob.type,'matrix_world':list(sum((list(row) for row in ob.matrix_world),[])),
           'parent':ob.parent.name if ob.parent else None,
           'parent_type':ob.parent_type,'parent_bone':ob.parent_bone}
        if ob.type=='MESH':
            me=ob.data;me.calc_loop_triangles()
            coords=attr_array(me.vertices,'co',3,np.float32)
            edges=attr_array(me.edges,'vertices',2,np.int32)
            r.update({'part_id':ob['part_id'],'lod_level':ob['lod_level'],
              'vertices':len(me.vertices),'edges':len(me.edges),'polygons':len(me.polygons),
              'triangles':len(me.loop_triangles),'positions_sha256':array_hash(coords),
              'edges_sha256':array_hash(edges),
              'polygons_sha256':data_hash([list(p.vertices) for p in me.polygons]),
              'smooth_faces_sha256':data_hash([p.use_smooth for p in me.polygons]),
              'uv_layers':{},'groups':{g.index:g.name for g in ob.vertex_groups},
              'weights_sha256':data_hash([[(g.group,g.weight) for g in v.groups] for v in me.vertices]),
              'modifiers':[{'name':m.name,'type':m.type,'target':m.object.name if m.type=='ARMATURE' and m.object else None,
                'show_viewport':m.show_viewport,'show_render':m.show_render,
                'use_vertex_groups':m.use_vertex_groups if m.type=='ARMATURE' else None,
                'use_deform_preserve_volume':m.use_deform_preserve_volume if m.type=='ARMATURE' else None} for m in ob.modifiers]})
            for uv in me.uv_layers:
                r['uv_layers'][uv.name]=array_hash(attr_array(uv.data,'uv',2,np.float32))
            if include_uv_samples:
                uv=attr_array(me.uv_layers[0].data,'uv',2,np.float32).astype(np.float64)
                loops=np.asarray([tri.loops[:] for tri in me.loop_triangles],dtype=np.int64)
                t=uv[loops]
                pts=np.concatenate((t[:,0],t[:,1],t[:,2],(t[:,0]+t[:,1])*.5,
                    (t[:,1]+t[:,2])*.5,(t[:,2]+t[:,0])*.5,t.mean(axis=1)))
                samples[ob.name]=pts
        elif ob.type=='ARMATURE':
            r['bones']={b.name:{'parent':b.parent.name if b.parent else None,
                'head':list(b.head_local),'tail':list(b.tail_local),'deform':b.use_deform,
                'matrix':list(sum((list(row) for row in b.matrix_local),[])),
                'inherit_scale':b.inherit_scale,'use_connect':b.use_connect}
                for b in ob.data.bones}
            r['pose']={b.name:list(sum((list(row) for row in b.matrix_basis),[])) for b in ob.pose.bones}
        records[ob.name]=r
    return records,samples

def png(path):
    """Decode raw 8-bit PNG samples without premultiplication or color conversion."""
    data=path.read_bytes();assert data[:8]==b'\x89PNG\r\n\x1a\n'
    pos=8;stream=[]
    while pos<len(data):
        length=struct.unpack('>I',data[pos:pos+4])[0];tag=data[pos+4:pos+8];body=data[pos+8:pos+8+length]
        assert zlib.crc32(tag+body)&0xffffffff==struct.unpack('>I',data[pos+8+length:pos+12+length])[0]
        if tag==b'IHDR':w,h,depth,ctype,compression,filter_method,interlace=struct.unpack('>IIBBBBB',body)
        if tag==b'IDAT':stream.append(body)
        pos+=12+length
    assert depth==8 and ctype in (0,2,4,6) and interlace==0,(path,depth,ctype,interlace)
    channels={0:1,2:3,4:2,6:4}[ctype];stride=w*channels
    rows=np.frombuffer(zlib.decompress(b''.join(stream)),dtype=np.uint8).reshape(h,stride+1)
    out=np.empty((h,stride),dtype=np.uint8)
    if np.all(rows[:,0]==0):return rows[:,1:].reshape(h,w,channels).copy()
    # Blender PNGs commonly use sub/up filters. Sequential rows reconstruct the
    # byte stream exactly; vectorized per-channel prefix sums handle sub.
    for y in range(h):
        f=int(rows[y,0]);raw=rows[y,1:];prior=out[y-1] if y else np.zeros(stride,dtype=np.uint8)
        if f==0:out[y]=raw
        elif f==1:
            for c in range(channels):out[y,c::channels]=np.cumsum(raw[c::channels],dtype=np.uint32)%256
        elif f==2:out[y]=raw+prior
        else:
            current=out[y]
            for x in range(stride):
                a=int(current[x-channels]) if x>=channels else 0;b=int(prior[x]);c=int(prior[x-channels]) if x>=channels else 0
                if f==3:predict=(a+b)//2
                elif f==4:
                    p=a+b-c;da=abs(p-a);db=abs(p-b);dc=abs(p-c)
                    predict=a if da<=db and da<=dc else b if db<=dc else c
                else:raise ValueError(f'Unexpected PNG filter {f}')
                current[x]=(int(raw[x])+predict)&255
    return out.reshape(h,w,channels)

def bilinear(im,uv):
    h,w=im.shape[:2];x=np.clip(uv[:,0]*w-.5,0,w-1);y=np.clip((1-uv[:,1])*h-.5,0,h-1)
    x0=x.astype(np.int64);y0=y.astype(np.int64);x1=np.minimum(x0+1,w-1);y1=np.minimum(y0+1,h-1)
    fx=(x-x0)[:,None];fy=(y-y0)[:,None]
    return ((1-fy)*((1-fx)*im[y0,x0]+fx*im[y0,x1])+fy*((1-fx)*im[y1,x0]+fx*im[y1,x1]))/255.

report={'status':'running','scope':'Read-only Blender/source texture verification; Unreal verification is separate.',
    'baseline_sha256':digest(BASELINE),'current_sha256':digest(CURRENT),'parameter_manifest_sha256':digest(PARAMS)}
before,_=capture(BASELINE)
after,samples=capture(CURRENT,True)
changed={name:[key for key in set(before.get(name,{}))|set(after.get(name,{})) if before.get(name,{}).get(key)!=after.get(name,{}).get(key)]
    for name in set(before)|set(after) if before.get(name)!=after.get(name)}
report['invariants']={'identical':not changed,'before_sha256':data_hash(before),'after_sha256':data_hash(after),
    'mesh_count':sum(r['type']=='MESH' for r in after.values()),'objects':len(after),'changed_fields':changed}
assert not changed,changed
manifest=json.loads(PARAMS.read_text());entries=manifest['parts'];by_part={e['part_id']:i for i,e in enumerate(entries)}
assert len(entries)==16
masks=[png(TEX/f'blacknunchucks_partmask{i}.png') for i in range(4)]
assert all(m.shape==(4096,4096,4) for m in masks)
total=np.zeros((4096,4096),dtype=np.uint16)
report['mask_files']=[]
for i,m in enumerate(masks):
    assert np.all((m==0)|(m==255))
    total+=np.sum(m,axis=2,dtype=np.uint16)
    report['mask_files'].append({'file':f'blacknunchucks_partmask{i}.png','sha256':digest(TEX/f'blacknunchucks_partmask{i}.png'),
        'rgba_channel_nonzero_pixels':np.count_nonzero(m,axis=(0,1)).tolist(),
        'rgb_data_survives_alpha_zero':bool(np.any(np.any(m[:,:,:3]>0,axis=2)&(m[:,:,3]==0)))})
assert np.all((total==0)|(total==255))
report['all_mask_pixels_exclusive']=True
report['uv_samples']=[]
for name,uv in samples.items():
    part=after[name]['part_id'];index=by_part[part];sampled=np.concatenate([bilinear(m,uv) for m in masks],axis=1)
    correct=sampled[:,index];wrong=np.delete(sampled,index,axis=1)
    record={'object':name,'part':part,'lod':after[name]['lod_level'],'samples':len(uv),
        'intended_channel_min':float(correct.min()),'unintended_channel_max':float(wrong.max()),
        'passed':bool(np.all(correct>1-1e-6) and np.all(wrong<1e-6))}
    report['uv_samples'].append(record);assert record['passed'],record
report['total_uv_samples']=sum(r['samples'] for r in report['uv_samples'])
report['mip_checks']=[]
for mip in range(1,7):
    masks=[m.astype(np.float32).reshape(m.shape[0]//2,2,m.shape[1]//2,2,4).mean(axis=(1,3)) for m in masks]
    low=1.;high=0.
    for name,uv in samples.items():
        index=by_part[after[name]['part_id']]
        # Corners/edges are included; no expensive pixel-wide oversampling needed.
        sampled=np.concatenate([bilinear(m,uv) for m in masks],axis=1)
        low=min(low,float(sampled[:,index].min()));high=max(high,float(np.delete(sampled,index,axis=1).max()))
    report['mip_checks'].append({'mip':mip,'size':4096//(2**mip),'minimum_intended_mask':low,'maximum_unintended_mask':high,
      'informational_only':True})
report['default_render']={}
original=png(RND/'BlackNunchucks_Front.png');default=png(RND/'BlackNunchucks_Recolor_DefaultCheck.png')
assert original.shape==default.shape
delta=np.abs(original.astype(np.int16)-default.astype(np.int16))
report['default_render']={'shape':list(original.shape),'identical_pixels':bool(np.all(delta==0)),
    'maximum_channel_delta_8bit':int(delta.max()),'mean_absolute_channel_delta_8bit':float(delta.mean()),
    'changed_channel_samples':int(np.count_nonzero(delta)),'total_channel_samples':int(delta.size)}
report['default_render']['negligible_rounding_only']=bool(delta.max()<=1 and np.count_nonzero(delta)/delta.size<.001)
assert report['default_render']['negligible_rounding_only'],report['default_render']
report['unchanged_original_pbr_textures']={}
with zipfile.ZipFile(ROOT/'Backups/BlackNunchucks_PreRecolor/BlackNunchucks_Package.zip') as old_package:
    for name in old_package.namelist():
        if name.startswith('Textures/BlackNunchucks/') and name.endswith('.png'):
            original_hash=hashlib.sha256(old_package.read(name)).hexdigest()
            path=ROOT/name
            report['unchanged_original_pbr_textures'][path.name]={'original_sha256':original_hash,
                'current_sha256':digest(path),'identical':digest(path)==original_hash}
assert len(report['unchanged_original_pbr_textures'])==5
assert all(v['identical'] for v in report['unchanged_original_pbr_textures'].values())
report['source_unchanged_during_validation']=digest(CURRENT)==report['current_sha256']
assert report['source_unchanged_during_validation']
report['status']='passed'
(WORK/'recolor_independent_qa.json').write_text(json.dumps(report,indent=2))
print('INDEPENDENT_RECOLOR_QA',json.dumps({k:v for k,v in report.items() if k not in ('uv_samples','mask_files')},indent=2),flush=True)
