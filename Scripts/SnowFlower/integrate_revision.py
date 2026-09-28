"""Integrate bounded component generators into the deterministic builder."""
from pathlib import Path
root=Path(__file__).resolve().parents[2]
p=root/'Scripts/SnowFlower/build_snow_flower.py'
s=(root/'WorkFiles/SnowFlower/Revision1/build_snow_flower.py').read_text(encoding='utf-8')
def module(name):return f"exec((ROOT/'Scripts/SnowFlower/{name}.py').read_text(encoding='utf-8'),globals())\n\n"
s=s.replace('asset_objects=[o for o in scene.objects',module('uv_helpers')+'asset_objects=[o for o in scene.objects')
s=s.replace("bpy.ops.uv.smart_project(angle_limit=math.radians(60),island_margin=.012);bpy.ops.object.mode_set(mode='OBJECT')","bpy.ops.uv.smart_project(angle_limit=math.radians(60),island_margin=.012);bpy.ops.object.mode_set(mode='OBJECT')\n    repair_collapsed_uv(ob.data)")
s=s.replace('def buffer(name,material,group):',module('metal_finish_revision')+'def buffer(name,material,group):')
s=s.replace('def blade_shape(z):',module('floral_revision')+'def blade_shape(z):')
a=s.index('# Fine irregular raised silver branches');b=s.index('def extrude(',a)
s=s[:a]+module('blade_revision')+s[b:]
a=s.index('wing=[');b=s.index('def collar(',a)
s=s[:a]+module('guard_revision')+s[b:]
a=s.index("collar('SF_Grip_Core'");b=s.index('# Side-attached cord',a)
s=s[:a]+module('hilt_revision')+s[b:]
a=s.index('# Side-attached cord');b=s.index('# Consolidated named components',a)
s=s[:a]+module('tassel_revision')+s[b:]
s=s.replace("bevel.width=.001;bevel.segments=3","bevel.width=.00032;bevel.segments=3")
# Reduce broad cloudiness and chrome-like contrast; retain physical micro detail.
s=s.replace('v*.68','v*.91').replace('v*1.22','v*1.07')
s=s.replace('rough-.055','rough-.025').replace('rough+.08','rough+.035')
s=s.replace("(.043,.054,.063),1,.32,90,.000019","(.040,.046,.050),1,.38,300,.000014")
s=s.replace("(.47,.51,.54),1,.23,250,.000008","(.40,.43,.45),1,.32,500,.000008")
s=s.replace("(.47,.47,.45),1,.255,160,.000012","(.44,.45,.44),1,.31,650,.000009")
s=s.replace("(.39,.415,.43),1,.31,360,.000009","(.40,.415,.42),1,.34,700,.000009")
s=s.replace("micro.inputs['Scale'].default_value=1750","micro.inputs['Scale'].default_value=2400")
s=s.replace("b.inputs['Strength'].default_value=.42;b.inputs['Distance'].default_value=.00016","b.inputs['Strength'].default_value=.55;b.inputs['Distance'].default_value=.00012")
s=s.replace("'guard_span':.134","'guard_span':.126")
s=s.replace("scene['asset']='Snow Flower — user reference interpretation'","scene['asset']='Snow Flower — reference revision 3'\nscene['revision']=3")
s=s.replace("scene.camera=cam","scene.camera=cam;cam.data.clip_start=.001")
s=s.replace("scene.view_settings.exposure=-.4","scene.view_settings.exposure=-.30")
s=s.replace("('Top',(-.1,-.4,1.7),25,.5,(1,.97,.92))","('Top',(-.1,-.4,1.7),25,.5,(1,.97,.92)),('PommelFill',(.10,-.25,-.48),7,.40,(1,.98,.94))")
# Camera-facing backdrop close to the white concept sheet, preserving lighting.
needle="studio=collection('STUDIO_ExcludeFromExport')"
insert="""wn=scene.world.node_tree.nodes;wl=scene.world.node_tree.links
wlight=wn.new('ShaderNodeLightPath');wmix=wn.new('ShaderNodeMixShader');wback=wn.new('ShaderNodeBackground')
wback.inputs['Color'].default_value=(1,1,1,1);wback.inputs['Strength'].default_value=4
wl.new(wlight.outputs['Is Camera Ray'],wmix.inputs[0]);wl.new(wn.get('Background').outputs[0],wmix.inputs[1]);wl.new(wback.outputs[0],wmix.inputs[2]);wl.new(wmix.outputs[0],wn.get('World Output').inputs[0])
"""
s=s.replace(needle,insert+needle)
# Improve guard view correspondence: nearer frontal, no excessive pitched angle.
s=s.replace("(.22,-.60,.23),(0,0,.120),.185","(.065,-.60,.090),(0,0,.128),.166")
s=s.replace("(.07,-.10,-.29),(0,0,-.145),.100","(.057,-.065,-.235),(0,0,-.152),.080")
p.write_text(s,encoding='utf-8')
print('Revision modules integrated')
