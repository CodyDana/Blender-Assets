"""Add the verified native Unreal recolor assets to the portable cloak pack."""
from pathlib import Path
import hashlib,json,shutil,runpy
ROOT=Path(r'C:\Users\Cody\Desktop\Blender_Projects');OUT=ROOT/'Exports/BlackCloak'
PROJECT=ROOT/'WorkFiles/BlackCloak/UnrealRecolor';DEST=OUT/'Unreal'
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
setup=json.loads((PROJECT/'Validation/recolor_setup_report.json').read_text(encoding='utf-8'))
verify=json.loads((PROJECT/'Validation/recolor_verify_report.json').read_text(encoding='utf-8'))
assert setup['status']=='saved_pending_fresh_process_verification',setup['status']
assert verify['status']=='passed',verify
for name,value in verify['verified_uasset_sha256'].items():assert digest(PROJECT/name)==value,name
report=json.loads((OUT/'asset_report.json').read_text(encoding='utf-8'))
assert digest(ROOT/'Assets/BlackCloak.blend')==report['editable_blend_sha256']
for name,value in setup['source_files_sha256'].items():assert digest(OUT/name)==value
for info in setup['textures'].values():
    texture_name=info['path'].split('/')[-1].split('.')[0]+'.png'
    assert digest(OUT/'Textures'/texture_name)==info['source_sha256']
DEST.mkdir(exist_ok=True)
for path in PROJECT.rglob('*'):
    if not path.is_file():continue
    rel=path.relative_to(PROJECT)
    if (rel.parts[:2]==('Content','BlackCloak') and path.suffix in {'.uasset','.umap','.ubulk','.uexp'}) or (rel.parts[0]=='Config' and path.suffix=='.ini') or path.name=='BlackCloakRecolor.uproject' or (rel.parts[0]=='Validation' and path.name in {'recolor_setup_report.json','recolor_verify_report.json'}):
        target=DEST/rel;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,target)
for name,value in verify['verified_uasset_sha256'].items():assert digest(DEST/name)==value,name
(DEST/'Scripts').mkdir(exist_ok=True)
for name in ('unreal_recolor_setup.py','unreal_recolor_verify.py'):
    shutil.copy2(ROOT/'Scripts/BlackCloak'/name,DEST/'Scripts'/name)
usage=(ROOT/'WorkFiles/BlackCloak/recolor_usage_draft.md').read_text(encoding='utf-8').split('\n---\n')[0]
intro='''# Recolorable cloak — Unreal Engine 5.8

This package includes a native Unreal material with a **CloakColor** control. No texture repainting is needed. Geometry and original Blender/FBX/GLB files retain their existing shape and black default appearance.

## Bring it into your game

1. Open `Unreal/BlackCloakRecolor.uproject` with Unreal Engine 5.8. The supplied assets were saved and reloaded in 5.8.2.
2. In the Content Browser, open `Content/BlackCloak`. Right-click the folder and choose **Migrate**, then choose your game's **Content** folder. This carries the meshes, materials and texture dependencies together.
3. Use `Meshes/SM_BlackCloak` for a static cloak, or `Meshes/SK_BlackCloak` for the existing skeleton attachment version. The cloth slots already use `Materials/MI_Cloak_Black`; the clasp and leather have separate materials.
4. Duplicate `MI_Cloak_Black` (or one of the Crimson, Navy, Ivory presets), open it, enable **CloakColor**, and choose your color.

The prepared Unreal meshes contain LOD0. The separate FBX LOD1/LOD2 files remain in the main package. Cloth simulation and character movement fitting are separate unfinished work.

## Included color assets

| Asset | Purpose |
| --- | --- |
| `M_Cloak_Recolor` | Parent material with adjustable cloth color and fabric detail |
| `MI_Cloak_Black` | Default black cloth |
| `MI_Cloak_Crimson` | Red example |
| `MI_Cloak_Navy` | Blue example |
| `MI_Cloak_Ivory` | Light-colored example |
| `M_Cloak_BlackenedSteel` | Separate clasp material |
| `M_Cloak_CharcoalLeather` | Separate attachment loop material |

'''
usage=usage.replace('# Recoloring the cloak in Unreal Engine','## Color controls',1)
(OUT/'RECOLOR.md').write_text(intro+usage,encoding='utf-8')
preview=OUT/'Previews/Recolor';preview.mkdir(exist_ok=True)
for path in (ROOT/'Renders/BlackCloak/Recolor').glob('*'):
    if path.suffix in {'.png','.json'}:shutil.copy2(path,preview/path.name)
cards=''.join(f'<figure><img src="Previews/Recolor/Cloak_{name}.png" alt="{name} cloak material preview"><figcaption>{name}</figcaption></figure>' for name in ('Black','Crimson','Navy','Ivory'))
(OUT/'RECOLOR.html').write_text('''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Recolorable cloak</title><style>body{background:#efeeeb;color:#242424;font:16px/1.5 system-ui;margin:0}main{max-width:1400px;margin:32px auto;padding:24px}h1{font-size:28px}p{max-width:900px}.presets{display:grid;grid-template-columns:repeat(4,1fr);gap:14px}figure{margin:0;background:white;border-radius:10px;overflow:hidden}img{display:block;width:100%}figcaption{padding:12px;font-weight:600}code{background:#ddd;padding:2px 5px}a{color:#285180}@media(max-width:700px){.presets{grid-template-columns:repeat(2,1fr)}}</style><main><h1>One cloak, adjustable color</h1><p>Open a supplied <code>MI_Cloak_*</code> material instance in Unreal and change <code>CloakColor</code>. The fabric retains its weave, roughness and normal detail; the clasp stays separate. These examples use the same color formula rendered in Blender, not Unreal screenshots. Your game's lighting will affect appearance.</p><div class="presets">'''+cards+'''</div><p><a href="RECOLOR.md">Unreal setup and runtime color instructions</a></p></main></html>''',encoding='utf-8')
report['unreal_recolor']={'engine':setup['engine'],'status':'saved_and_fresh_process_verified','project':'Unreal/BlackCloakRecolor.uproject','master':setup['master_material'],'color_parameter':'CloakColor','fabric_detail_parameter':'FabricDetail','presets_linear':setup['presets_linear'],'grain_reference_linear':setup['grain_reference_linear'],'verification':'Unreal/Validation/recolor_verify_report.json','original_geometry_unchanged':True,'limits':setup['limits']}
(OUT/'asset_report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
runpy.run_path(str(ROOT/'Scripts/BlackCloak/package_reference_revision.py'),run_name='__main__')
print('UNREAL_RECOLOR_PACKAGED')
