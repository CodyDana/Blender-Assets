"""Create the editable male MetaHuman and render its real engine preview."""
from pathlib import Path
import unreal as ue,json,time,traceback
ROOT=Path(r'C:\Users\Cody\Desktop\Blender_Projects')
OUT=ROOT/'WorkFiles/MetaHuman/male_preview';OUT.mkdir(parents=True,exist_ok=True)
DEST='/Game/Characters/MetaHumans/MH_MaleBase'
PRESET='/MetaHumanCharacter/Optional/Presets/Kelvin'
report={'engine':ue.SystemLibrary.get_engine_version(),'preset':PRESET,'asset':DEST,'status':'starting','captures':[]}
def checkpoint(status):
    report['status']=status;(OUT/'report.json').write_text(json.dumps(report,indent=2));ue.log('MH_PREVIEW '+status)
try:
    existing=ue.load_asset(DEST) if ue.EditorAssetLibrary.does_asset_exist(DEST) else None
    character=existing or ue.EditorAssetLibrary.duplicate_asset(PRESET,DEST)
    assert character and isinstance(character,ue.MetaHumanCharacter)
    assert ue.EditorAssetLibrary.save_loaded_asset(character,only_if_is_dirty=False)
    checkpoint('editable_character_saved')
    ue.EditorLevelLibrary.new_level('/Game/Review/TemporaryMalePreview')
    world=ue.get_editor_subsystem(ue.UnrealEditorSubsystem).get_editor_world()
    actors=ue.get_editor_subsystem(ue.EditorActorSubsystem)
    subsystem=ue.get_editor_subsystem(ue.MetaHumanCharacterEditorSubsystem)
    assert subsystem.try_add_object_to_edit(character),'Failed to initialize installed MetaHuman data'
    checkpoint('character_open_for_editing')
    actor=subsystem.spawn_meta_human_actor(character,True)
    assert actor
    subsystem.assemble_for_preview(character)
    for command in ['r.DynamicGlobalIlluminationMethod 0','r.ReflectionMethod 0','r.AmbientOcclusionLevels 0','r.DistanceFieldAO 0','r.RayTracing.ForceAllRayTracingEffects 0','r.AntiAliasingMethod 2']:
        ue.SystemLibrary.execute_console_command(world,command)
    report['actor_class']=actor.get_class().get_name()
    report['components']=[{'name':c.get_name(),'class':c.get_class().get_name()} for c in actor.get_components_by_class(ue.ActorComponent)]
    report['has_high_resolution_textures']=character.get_editor_property('has_high_resolution_textures')
    report['can_build']=subsystem.can_build_meta_human(character,False)
    ue.EditorAssetLibrary.save_loaded_asset(character,only_if_is_dirty=False)
    def spawn(cls,location=(0,0,0),rotation=(0,0,0)):
        return actors.spawn_actor_from_class(cls,ue.Vector(*location),ue.Rotator(*rotation))
    for rot,intensity,color in [((-30,-125,0),5,(1,.94,.88)),((-15,-30,0),3,(.88,.93,1)),((-30,90,0),2,(1,1,1))]:
        light=spawn(ue.DirectionalLight,rotation=rot);light.light_component.set_intensity(intensity)
        light.light_component.set_light_color(ue.LinearColor(*color,1));light.light_component.set_cast_shadows(False)
    backdrop=spawn(ue.StaticMeshActor);backdrop.static_mesh_component.set_static_mesh(ue.load_asset('/Engine/BasicShapes/Sphere'))
    backdrop.set_actor_scale3d(ue.Vector(50,50,50));backdrop.static_mesh_component.set_cast_shadow(False)
    material=ue.new_object(ue.Material);material.set_editor_property('two_sided',True)
    material.set_editor_property('shading_model',ue.MaterialShadingModel.MSM_UNLIT)
    node=ue.MaterialEditingLibrary.create_material_expression(material,ue.MaterialExpressionConstant3Vector)
    node.set_editor_property('constant',ue.LinearColor(.18,.18,.18,1))
    ue.MaterialEditingLibrary.connect_material_property(node,'',ue.MaterialProperty.MP_EMISSIVE_COLOR)
    ue.MaterialEditingLibrary.recompile_material(material);backdrop.static_mesh_component.set_material(0,material)
    sky=spawn(ue.SkyLight);sky.light_component.set_mobility(ue.ComponentMobility.MOVABLE);sky.light_component.set_intensity(2)
    sky.light_component.recapture_sky()
    camera=spawn(ue.SceneCapture2D);capture=camera.get_component_by_class(ue.SceneCaptureComponent2D)
    target=ue.RenderingLibrary.create_render_target2d(world,1000,1200,ue.TextureRenderTargetFormat.RTF_RGBA8)
    target.set_editor_property('target_gamma',2.2)
    capture.set_editor_property('texture_target',target);capture.set_editor_property('capture_source',ue.SceneCaptureSource.SCS_FINAL_COLOR_LDR)
    capture.set_editor_property('capture_every_frame',True);capture.set_editor_property('always_persist_rendering_state',True)
    capture.set_editor_property('fov_angle',30.)
    pp=capture.get_editor_property('post_process_settings')
    for key,val in [('override_auto_exposure_method',True),('auto_exposure_method',ue.AutoExposureMethod.AEM_MANUAL),('override_auto_exposure_bias',True),('auto_exposure_bias',0.),('override_auto_exposure_apply_physical_camera_exposure',True),('auto_exposure_apply_physical_camera_exposure',False),('override_vignette_intensity',True),('vignette_intensity',0.)]:pp.set_editor_property(key,val)
    capture.set_editor_property('post_process_settings',pp)
    report['bounds']=str(actor.get_actor_bounds(False))
    shots=[('Body',(0,430,100),(0,0,92)),('Face',(0,110,168),(0,0,164)),('FaceThreeQuarter',(-55,110,168),(0,0,164))]
    state={'frame':0,'index':0,'capture_at':float('inf')}
    def configure():
        _,pos,look=shots[state['index']];pos=ue.Vector(*pos);look=ue.Vector(*look)
        camera.set_actor_location_and_rotation(pos,ue.MathLibrary.find_look_at_rotation(pos,look),False,False)
        ue.AutomationLibrary.finish_loading_before_screenshot();state['capture_at']=time.monotonic()+4
    def tick(delta):
        try:
            state['frame']+=1
            if state['frame']==140:configure()
            if time.monotonic()>=state['capture_at']:
                name=shots[state['index']][0];capture.capture_scene()
                ue.RenderingLibrary.export_render_target(world,target,str(OUT),name+'.png')
                report['captures'].append(name+'.png');checkpoint('captured_'+name)
                state['index']+=1
                if state['index']==len(shots):
                    ue.EditorAssetLibrary.save_loaded_asset(character,only_if_is_dirty=False)
                    subsystem.remove_object_to_edit(character)
                    checkpoint('editable_character_saved_and_previewed')
                    ue.unregister_slate_post_tick_callback(state['callback']);ue.SystemLibrary.quit_editor()
                else:configure()
        except Exception:
            report['error']=traceback.format_exc();checkpoint('failed');ue.log_error(report['error'])
            ue.unregister_slate_post_tick_callback(state['callback']);ue.SystemLibrary.quit_editor()
    state['callback']=ue.register_slate_post_tick_callback(tick);ue.EditorPythonScripting.set_keep_python_script_alive(True)
    checkpoint('render_warmup')
except Exception:
    report['error']=traceback.format_exc();checkpoint('failed');ue.log_error(report['error']);ue.SystemLibrary.quit_editor()
