"""Fresh-process verification of saved Unreal recolor assets and runtime MIDs.

Run with UnrealEditor-Cmd PROJECT -run=pythonscript -script=THIS_FILE
-AllowCommandletRendering -unattended -nosound. Uses real shader compilation.
Does not save or alter source assets; test components/MIDs are transient.
"""
from pathlib import Path
import json,hashlib,traceback
import unreal
PROJECT=Path(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir()))
REPORT=PROJECT/'Validation/recolor_verify_report.json'
setup=json.loads((PROJECT/'Validation/recolor_setup_report.json').read_text(encoding='utf-8'))
M=unreal.MaterialEditingLibrary
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def rgb(c):return [float(c.r),float(c.g),float(c.b)]
def close(a,b):return len(a)==len(b) and max(abs(x-y) for x,y in zip(a,b))<1e-6
def main():
    r={'status':'running','engine':unreal.SystemLibrary.get_engine_version(),'checks':{},'presets':{},'mesh_slots':{},'runtime_mid':{},'scope':'Fresh-process saved assets, shader compilation, transient component recoloring; no gameplay/cloth simulation test.'}
    files=list((PROJECT/'Content/BlackCloak').rglob('*.uasset'))
    before={str(p.relative_to(PROJECT)):sha(p) for p in files}
    def check(key,condition):
        r['checks'][key]=bool(condition)
        assert condition,key
    try:
        check('setup_completed',setup['status']=='saved_pending_fresh_process_verification')
        master=unreal.load_asset(setup['master_material'])
        check('master_loaded',isinstance(master,unreal.Material))
        check('skeletal_usage',master.get_editor_property('used_with_skeletal_mesh'))
        vectors=[str(x) for x in M.get_vector_parameter_names(master)]
        scalars=[str(x) for x in M.get_scalar_parameter_names(master)]
        check('color_parameter_exposed','CloakColor' in vectors)
        check('detail_controls_exposed',all(x in scalars for x in ('FabricDetail','NormalStrength','RoughnessMultiplier')))
        nodes={str(n.get_editor_property('desc')):n for n in M.get_material_expressions(master)}
        check('bounded_grain_reference',abs(nodes['Normalize neutral grain'].get_editor_property('const_b')-.013702083)<1e-8)
        for edge in setup['graph_connections']:
            if len(edge)==4:
                check('connection_'+edge[0]+'_to_'+edge[2],nodes[edge[0]] in M.get_inputs_for_material_expression(master,nodes[edge[2]]))
        for label,prop in [('Clamp base color',unreal.MaterialProperty.MP_BASE_COLOR),('Clamp roughness',unreal.MaterialProperty.MP_ROUGHNESS),('Normalize tangent normal',unreal.MaterialProperty.MP_NORMAL)]:
            check('output_'+label,M.get_material_property_input_node(master,prop)==nodes[label])
        for key,info in setup['textures'].items():
            texture=unreal.load_asset(info['path'])
            check('texture_'+key+'_srgb',bool(texture.get_editor_property('srgb'))==info['srgb'])
            if key=='normal':check('dx_normal_no_double_flip',not texture.get_editor_property('flip_green_channel'))
        instances={}
        for name,path in setup['instances'].items():
            inst=unreal.load_asset(path);instances[name]=inst
            check(name+'_parent',inst.get_editor_property('parent')==master)
            value=rgb(M.get_material_instance_vector_parameter_value(inst,'CloakColor'))
            check(name+'_saved_color',close(value,setup['presets_linear'][name]))
            for parameter in ('FabricDetail','NormalStrength','RoughnessMultiplier'):
                check(name+'_'+parameter,abs(M.get_material_instance_scalar_parameter_value(inst,parameter)-1)<1e-6)
            r['presets'][name]=value
        meshes={}
        for entry in setup['meshes']:
            mesh=unreal.load_asset(entry['path']);meshes[entry['skeletal']]=mesh
            slots=list(mesh.get_editor_property('materials' if entry['skeletal'] else 'static_materials'))
            actual=[slot.get_editor_property('material_interface').get_path_name() for slot in slots]
            expected=[slot['material'] for slot in entry['material_slots']]
            check(('skeletal' if entry['skeletal'] else 'static')+'_material_assignments',actual==expected)
            r['mesh_slots'][entry['path']]=actual
            if entry['skeletal']:
                skeleton=mesh.get_editor_property('skeleton')
                check('skeletal_dependency_loaded',isinstance(skeleton,unreal.Skeleton))
                check('skeletal_dependency_persisted',skeleton.get_path_name()==entry['skeleton'])
                component=unreal.SkeletalMeshComponent()
                component.set_skeletal_mesh_asset(mesh)
                bones=[str(component.get_bone_name(i)) for i in range(component.get_num_bones())]
                r['skeleton']={'path':skeleton.get_path_name(),'bone_count':len(bones),'bones':bones}
                canonical={b.replace('.','_') for b in bones}
                check('attachment_bones_present',all(b in canonical for b in ('neck01','clavicle_R','spine01')))
        # Actual primitive-component MID creation/assignment, not just math.
        entry=next(x for x in setup['meshes'] if not x['skeletal'])
        cloth=[x['index'] for x in entry['material_slots'] if 'MI_Cloak_' in x['material']]
        check('cloth_slot_distinct',cloth==[2])
        components=[];mids=[]
        for name,test_color in [('A',[.2,.5,.08]),('B',[.04,.03,.6])]:
            comp=unreal.StaticMeshComponent();comp.set_static_mesh(meshes[False]);components.append(comp)
            hardware=[comp.get_material(i) for i in (0,1)]
            mid=comp.create_dynamic_material_instance(cloth[0],instances['Black']);mids.append(mid)
            check(name+'_mid_assigned',comp.get_material(cloth[0])==mid)
            mid.set_vector_parameter_value('CloakColor',unreal.LinearColor(*test_color,1))
            getter=getattr(mid,'get_vector_parameter_value',None) or getattr(mid,'k2_get_vector_parameter_value')
            actual=rgb(getter('CloakColor'))
            check(name+'_runtime_color',close(actual,test_color))
            check(name+'_hardware_unchanged',all(comp.get_material(i)==hardware[i] for i in (0,1)))
            r['runtime_mid'][name]={'color':actual,'cloth_slot':cloth[0],'hardware_unchanged':True}
        check('independent_dynamic_instances',mids[0]!=mids[1])
        check('shared_black_preset_unchanged',close(rgb(M.get_material_instance_vector_parameter_value(instances['Black'],'CloakColor')),setup['presets_linear']['Black']))
        # get_statistics waits for shader-map compilation in this engine.
        stats=M.get_statistics(master)
        r['shader_statistics']={name:int(stats.get_editor_property(name)) for name in ('num_vertex_shader_instructions','num_pixel_shader_instructions','num_samplers','num_pixel_texture_samples')}
        check('shader_compiled',r['shader_statistics']['num_pixel_shader_instructions']>0)
        after={str(p.relative_to(PROJECT)):sha(p) for p in files}
        check('saved_asset_bytes_unchanged_during_verify',before==after)
        r['verified_uasset_sha256']=after
        r['status']='passed'
    except Exception:
        r['status']='failed';r['error']=traceback.format_exc();unreal.log_error(r['error'])
    REPORT.write_text(json.dumps(r,indent=2),encoding='utf-8')
    unreal.log('BLACKCLOAK_RECOLOR_VERIFY '+r['status'])
    if r['status']!='passed':raise RuntimeError(r.get('error','Verification failed'))
if __name__=='__main__':main()
