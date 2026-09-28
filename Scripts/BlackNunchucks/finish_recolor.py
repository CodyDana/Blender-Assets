"""Attach verified Unreal recolor evidence and assemble a clean native project."""
from pathlib import Path
import json, hashlib, shutil
ROOT=Path(__file__).resolve().parents[2]
WORK=ROOT/'WorkFiles/BlackNunchucks/RecolorUnreal'; OUT=ROOT/'Exports/BlackNunchucks'
digest=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
source=json.loads((WORK/'setup_report.json').read_text())
verified=json.loads((WORK/'reload_report.json').read_text())
assert source['status']=='passed' and verified['status']=='passed'
assert verified['fresh_process'] and not verified['compile_errors']
assert len(verified['gpu_mask_isolation']['tests'])==16
for p,h in verified['matching_source_sha256'].items(): assert digest(p)==h,p
assert len(verified['runtime_mid_tests'])==16 and verified['runtime_texture_swap']
demo=OUT/'UnrealDemo'; (demo/'Config').mkdir(parents=True,exist_ok=True)
content=WORK/'Project/Content/BlackNunchucks'
files=sorted(content.rglob('*.uasset'))
assert len(files)>=13
native={}
for p in files:
    target=demo/'Content/BlackNunchucks'/p.relative_to(content)
    target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,target)
    assert digest(target)==digest(p)
    native[str(target.relative_to(OUT)).replace('\\','/')]=digest(target)
uproject={'FileVersion':3,'EngineAssociation':'5.8','Category':'','Description':'Black Nunchucks: independent part recoloring',
          'Plugins':[{'Name':'PythonScriptPlugin','Enabled':True},{'Name':'EditorScriptingUtilities','Enabled':True},{'Name':'AndroidFileServer','Enabled':False}]}
(demo/'BlackNunchucksRecolor.uproject').write_text(json.dumps(uproject,indent=2))
(demo/'Config/DefaultEngine.ini').write_text('[ConsoleVariables]\nInterchange.FeatureFlags.Import.FBX=0\n\n[/Script/Engine.RendererSettings]\nr.AllowStaticLighting=False\nr.RayTracing=False\nr.DynamicGlobalIlluminationMethod=0\nr.ReflectionMethod=0\n')
verified['native_asset_sha256']=native
verified['source_blend_sha256']=digest(ROOT/'Assets/BlackNunchucks.blend')
verified['scope']='UE5.8 skeletal mesh/3 LOD import, persisted one-slot material assignment, shader compilation, 16 independent runtime color/amount controls, texture swapping, and D3D12 GPU mask isolation. Gameplay UI/physics/animations are not supplied.'
(OUT/'unreal_recolor_validation.json').write_text(json.dumps(verified,indent=2))
(OUT/'unreal_recolor_import.json').write_text(json.dumps(source,indent=2))
report=json.loads((OUT/'asset_report.json').read_text())
assert report['source_sha256']==verified['source_blend_sha256']
report['unreal_recolor']={'status':'passed','engine':verified['engine'],'report':'unreal_recolor_validation.json',
                         'report_sha256':digest(OUT/'unreal_recolor_validation.json'),'source_sha256':verified['source_blend_sha256'],
                         'scope':verified['scope']}
(OUT/'asset_report.json').write_text(json.dumps(report,indent=2))
print(json.dumps({'native_assets':len(native),'engine':verified['engine'],'status':'passed','output':str(demo)},indent=2))
