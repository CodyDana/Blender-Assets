"""Add lossless per-part masks and a Blender preview of the Unreal color controls.

The exchange material remains the original simple baked PBR material. Unreal's
master is created by unreal_recolor_setup.py; this script never changes geometry.
"""
from pathlib import Path
import bpy, numpy as np, json, hashlib, struct, zlib, sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'Scripts'))
from pipeline.lock import assert_owner
from pipeline.textures import image_pixels, load_data_image, write_png
assert_owner('BlackNunchucks','codex')
WORK=ROOT/'WorkFiles/BlackNunchucks'; TEX=ROOT/'Textures/BlackNunchucks'; REND=ROOT/'Renders/BlackNunchucks'
SOURCE=ROOT/'Assets/BlackNunchucks.blend'
before_sha=hashlib.sha256(SOURCE.read_bytes()).hexdigest()
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
parts=['grip_L','grip_R','cap_L','cap_R','eye_L','eye_R']+[f'chain_{i:02d}' for i in range(1,8)]+['weld_03','weld_04','weld_05']
params=['Grip_L','Grip_R','Cap_L','Cap_R','Eye_L','Eye_R']+[f'Chain_{i:02d}' for i in range(1,8)]+['Weld_03','Weld_04','Weld_05']
SIZE=4096; PAD=31
objects=[o for o in bpy.data.collections['BLACK_NUNCHUCKS'].objects if o.type=='MESH']
def signature():
    h=hashlib.sha256()
    for o in sorted(bpy.data.collections['BLACK_NUNCHUCKS'].objects,key=lambda o:o.name):
        h.update(o.name.encode());h.update(str(tuple(tuple(r) for r in o.matrix_world)).encode())
        if o.type=='MESH':
            for v in o.data.vertices:
                h.update(struct.pack('<3f',*v.co))
                h.update(str([(g.group,g.weight) for g in v.groups]).encode())
            for p in o.data.polygons:h.update(struct.pack('<'+'I'*len(p.vertices),*p.vertices))
            for uv in o.data.uv_layers:
                h.update(uv.name.encode())
                for d in uv.data:h.update(struct.pack('<2f',*d.uv))
        if o.type=='ARMATURE':
            for b in o.data.bones:
                h.update(str((b.name,b.parent.name if b.parent else None,tuple(b.head_local),tuple(b.tail_local),tuple(tuple(r) for r in b.matrix_local))).encode())
    return h.hexdigest()
before_geometry=signature()
charts=json.loads((WORK/'build_report.json').read_text())['charts']
labels=np.full((SIZE,SIZE),-1,dtype=np.int16)
report={'source_before_sha256':before_sha,'geometry_uv_weights_rig_before':before_geometry,
        'resolution':SIZE,'padding_px':PAD,'default_amount':0,'parts':[],
        'shader':'For each part: lerp(previousBaseColor, TintDetail.rgb * Color_part.rgb, PartMaskChannel * clamp(Amount_part,0,1))',
        'normal_and_orm':'Unchanged original PBR textures; DX normal for Unreal',
        'mask_encoding':'Four linear RGBA one-hot textures; independent alpha, no sRGB, no alpha discard',
        'textures':{}}
for i,(part,param) in enumerate(zip(parts,params)):
    owned={k:v for k,v in charts.items() if k.startswith(part+'_')}
    assert owned,part
    for name,(x,y,w,h) in owned.items():
        x0=max(0,int(np.floor(x*SIZE))-PAD);x1=min(SIZE,int(np.ceil((x+w)*SIZE))+PAD)
        y0=max(0,int(np.floor(y*SIZE))-PAD);y1=min(SIZE,int(np.ceil((y+h)*SIZE))+PAD)
        old=labels[y0:y1,x0:x1]
        assert np.all((old==-1)|(old==i)),(part,name,'padding overlaps another part')
        labels[y0:y1,x0:x1]=i
    largest=max(owned,key=lambda k:owned[k][2]*owned[k][3]);x,y,w,h=owned[largest]
    uv=[x+w*.5,y+h*.5]
    report['parts'].append({'part_id':part,'parameter_suffix':param,'mask_index':i//4,'channel':'RGBA'[i%4],
         'color_parameter':'Color_'+param,'amount_parameter':'Amount_'+param,'blender_sample_uv':uv,
         'texture_sample_uv_top_left':[uv[0],1-uv[1]],'charts':list(owned),
         'mask_pixels':int(np.sum(labels==i))})

# Verify the atlas regions cover the actual UVs of every LOD, including the eye
# end-cap islands whose chart names differ between LODs.
report['uv_coverage_checks']=[]
for o in objects:
    index=parts.index(o['part_id']);uv=o.data.uv_layers[0]
    coords=np.array([d.uv[:] for d in uv.data],dtype=np.float64)
    xy=np.clip(np.floor(coords*SIZE).astype(int),0,SIZE-1)
    assert np.all(labels[xy[:,1],xy[:,0]]==index),(o.name,'unmasked UV corner')
    report['uv_coverage_checks'].append({'object':o.name,'lod':o['lod_level'],'uv_corners':len(coords),'all_correct':True})

def chunk(tag,data):return struct.pack('!I',len(data))+tag+data+struct.pack('!I',zlib.crc32(tag+data)&0xffffffff)
def rgba_png(path,arr):
    # Exact data bytes preserve RGB even where the independent A mask is zero.
    a=np.asarray(arr,dtype=np.uint8)[::-1]
    scan=b''.join(b'\0'+row.tobytes() for row in a)
    data=b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('!2I5B',SIZE,SIZE,8,6,0,0,0))+chunk(b'IDAT',zlib.compress(scan,6))+chunk(b'IEND',b'')
    path.write_bytes(data)
mask_images=[]
for mi in range(4):
    arr=np.stack([(labels==mi*4+c).astype(np.uint8)*255 for c in range(4)],axis=2)
    path=TEX/f'blacknunchucks_partmask{mi}.png';rgba_png(path,arr)
    im=bpy.data.images.load(str(path),check_existing=False)
    im.name=f'T_BlackNunchucks_PartMask{mi}';im.colorspace_settings.name='Non-Color';im.alpha_mode='CHANNEL_PACKED';im.reload()
    raw=image_pixels(im)
    assert np.max(np.abs(raw-arr/255.0))<.001,('RGBA roundtrip',mi)
    del raw,arr
    im.pack();im.filepath='//../Textures/BlackNunchucks/'+path.name;mask_images.append(im)
    report['textures'][path.name]={'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'srgb':False,'channels':'RGBA independent'}

source=bpy.data.images.load(str(TEX/'blacknunchucks_basecolor.png'),check_existing=False)
source.colorspace_settings.name='Non-Color';source.reload()
rgb=image_pixels(source)[:,:,:3].copy();bpy.data.images.remove(source)
linear=np.where(rgb<=.04045,rgb/12.92,((rgb+.055)/1.055)**2.4)
lum=linear@np.array([.2126,.7152,.0722],dtype=np.float32)
detail=np.ones((SIZE,SIZE,4),dtype=np.float32)
for i,entry in enumerate(report['parts']):
    coverage=(labels==i);valid=coverage&(lum>1e-5)
    white=float(np.percentile(lum[valid],99.5))
    values=np.clip(lum[valid]/white,.15,1)
    for c in range(3):detail[:,:,c][valid]=values
    entry['neutralization_white_linear']=white
    entry['neutral_detail_range']=[float(values.min()),float(values.max())]
    # Missing LOD0 bake on deeply embedded LOD1/2 eye end faces uses neutral1.
    entry['unbaked_padding_pixels_neutral']=int(np.sum(coverage&~valid))
path=TEX/'blacknunchucks_tintdetail.png';write_png(detail,path)
im=load_data_image(path,'T_BlackNunchucks_TintDetail');im.pack();im.filepath='//../Textures/BlackNunchucks/'+path.name
report['textures'][path.name]={'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'srgb':False,'meaning':'Neutral linear grain modulation, black pigment removed'}
del detail,lum,linear,rgb,coverage,valid,values

original=bpy.data.materials['M_BlackNunchucks_Baked']
old=bpy.data.materials.get('M_BlackNunchucks_RecolorPreview')
if old:bpy.data.materials.remove(old,do_unlink=True)
mat=original.copy();mat.name='M_BlackNunchucks_RecolorPreview';mat.use_fake_user=True
mat['purpose']='Optional Blender preview of Unreal Color_* and Amount_* controls. Default portable export uses M_BlackNunchucks_Baked.'
nt=mat.node_tree;p=next(n for n in nt.nodes if n.type=='BSDF_PRINCIPLED')
base=p.inputs['Base Color'].links[0].from_socket
detailnode=nt.nodes.new('ShaderNodeTexImage');detailnode.image=im;detailnode.name='Texture_TintDetail';detailnode.location=(-1800,600)
channels=[]
for i,image in enumerate(mask_images):
    tex=nt.nodes.new('ShaderNodeTexImage');tex.image=image;tex.name=f'Texture_PartMask{i}';tex.location=(-2200,-i*450)
    separate=nt.nodes.new('ShaderNodeSeparateColor');nt.links.new(tex.outputs['Color'],separate.inputs[0]);separate.location=(-1900,-i*450)
    channels.extend([separate.outputs['Red'],separate.outputs['Green'],separate.outputs['Blue'],tex.outputs['Alpha']])
for i,(suffix,mask) in enumerate(zip(params,channels)):
    color=nt.nodes.new('ShaderNodeRGB');color.name='Color_'+suffix;color.label=color.name;color.outputs[0].default_value=(1,1,1,1);color.location=(-1600,-i*210)
    amount=nt.nodes.new('ShaderNodeValue');amount.name='Amount_'+suffix;amount.label=amount.name;amount.outputs[0].default_value=0;amount.location=(-1600,-i*210-80)
    alpha=nt.nodes.new('ShaderNodeMath');alpha.operation='MULTIPLY';alpha.location=(-1300,-i*210);nt.links.new(mask,alpha.inputs[0]);nt.links.new(amount.outputs[0],alpha.inputs[1])
    tint=nt.nodes.new('ShaderNodeMixRGB');tint.blend_type='MULTIPLY';tint.inputs[0].default_value=1;tint.location=(-1100,-i*210)
    nt.links.new(detailnode.outputs[0],tint.inputs[1]);nt.links.new(color.outputs[0],tint.inputs[2])
    mix=nt.nodes.new('ShaderNodeMixRGB');mix.blend_type='MIX';mix.name='Recolor_'+suffix;mix.location=(-800+i*210,350)
    nt.links.new(alpha.outputs[0],mix.inputs[0]);nt.links.new(base,mix.inputs[1]);nt.links.new(tint.outputs[0],mix.inputs[2]);base=mix.outputs[0]
nt.links.new(base,p.inputs['Base Color']);p.location=(2900,350)
assert signature()==before_geometry
report['geometry_uv_weights_rig_after']=signature();report['geometry_unchanged']=True
bpy.context.scene['recolor_setup']='16 part masks + neutral detail; Unreal setup script and optional M_BlackNunchucks_RecolorPreview included. Amount0 preserves original.'
bpy.ops.wm.save_as_mainfile(filepath=str(SOURCE))
report['source_after_sha256']=hashlib.sha256(SOURCE.read_bytes()).hexdigest()
(WORK/'recolor_report.json').write_text(json.dumps(report,indent=2))
(ROOT/'Exports/BlackNunchucks/recolor_parameters.json').write_text(json.dumps(report,indent=2))
print('RECOLOR_MASKS_AND_SOURCE_READY',flush=True)

# Renders use the equivalent shader for visible proof, without saving altered
# colors over the default asset or baking the Unreal controls into the exports.
s=bpy.context.scene
prefs=bpy.context.preferences.addons['cycles'].preferences;prefs.compute_device_type='OPTIX';prefs.get_devices()
for device in prefs.devices:device.use=device.type!='CPU'
s.cycles.device='GPU';s.cycles.samples=96
for o in objects:o.data.materials[0]=mat
s.render.filepath=str(REND/'BlackNunchucks_Recolor_DefaultCheck.png');bpy.ops.render.render(write_still=True)
demo=[(.65,.012,.018),(.8,.82,.75),(.78,.39,.07),(.055,.14,.7),(.8,.7,.45),(.35,.6,.8),
      (.7,.09,.02),(.02,.5,.65),(.65,.4,.04),(.35,.02,.55),(.03,.55,.15),(.65,.03,.23),(.035,.2,.65),
      (.65,.4,.04),(.35,.02,.55),(.03,.55,.15)]
for suffix,value in zip(params,demo):
    nt.nodes['Color_'+suffix].outputs[0].default_value=(*value,1)
    nt.nodes['Amount_'+suffix].outputs[0].default_value=1
s.render.filepath=str(REND/'BlackNunchucks_Recolor_Demo.png');bpy.ops.render.render(write_still=True)
report['demo_colors_linear']={suffix:list(value) for suffix,value in zip(params,demo)}
(WORK/'recolor_report.json').write_text(json.dumps(report,indent=2))
(ROOT/'Exports/BlackNunchucks/recolor_parameters.json').write_text(json.dumps(report,indent=2))
print('RECOLOR_PREVIEWS_COMPLETE',flush=True)
