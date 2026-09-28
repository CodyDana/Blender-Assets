"""Preserve the existing character and prepare an isolated MetaHuman project."""
from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,shutil
ROOT=Path(r'C:\Users\Cody\Desktop\Blender_Projects')
PROJECT=ROOT/'Exports/CharacterLab/Unreal'
STAMP=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
BACKUP=ROOT/'Backups'/('BeforeMetaHuman_'+STAMP)
def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for data in iter(lambda:f.read(8*1024*1024),b''):h.update(data)
    return h.hexdigest()
paths=[ROOT/'Assets/JinMuWon_v2.blend',*sorted((ROOT/'Assets/JinMuWon_v2').glob('*.blend'))]
paths += [ROOT/'Exports/JinMuWon_v2'/p for p in ['material_manifest.json','module_report.json','asset_report.json','CUSTOMIZATION.md','REVIEW_PLAN.md','README.md']]
paths += [ROOT/'Exports/JinMuWon_v2/Textures/T_Character_Fingernails_Mask.png']
records=[]
for source in paths:
    target=BACKUP/source.relative_to(ROOT);target.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(source,target)
    digest=sha(source);assert digest==sha(target)
    records.append({'source':str(source),'backup':str(target),'sha256':digest,'bytes':source.stat().st_size})
(BACKUP/'manifest.json').write_text(json.dumps({'date':STAMP,'status':'verified','files':records},indent=2))
for folder in [PROJECT/'Config',PROJECT/'Content',PROJECT/'Validation',ROOT/'WorkFiles/MetaHuman']:
    folder.mkdir(parents=True,exist_ok=True)
project_file=PROJECT/'CharacterLab.uproject'
assert not project_file.exists(),'Comparison project already exists; do not overwrite it'
project_file.write_text(json.dumps({'FileVersion':3,'EngineAssociation':'5.8','Category':'Character Development',
    'Description':'Isolated male MetaHuman evaluation. Previous custom character preserved separately.',
    'Plugins':[{'Name':name,'Enabled':True} for name in ['PythonScriptPlugin','EditorScriptingUtilities','MetaHumanCharacter']]},indent=2))
(PROJECT/'Config/DefaultEngine.ini').write_text('[/Script/EngineSettings.GameMapsSettings]\nEditorStartupMap=/Engine/Maps/Entry\nGameDefaultMap=/Engine/Maps/Entry\n\n[/Script/Engine.RendererSettings]\nr.AllowStaticLighting=False\nr.SkinCache.CompileShaders=True\nr.DefaultFeature.AutoExposure=False\n')
status={'active_work':'Male MetaHuman comparison','previous_character':'Preserved in place, further custom-body edits on hold',
        'backup':str(BACKUP),'comparison_project':str(project_file),'metahuman_asset_status':'Not created; Core Data component missing',
        'source_asset_count':len(records)}
(ROOT/'WorkFiles/MetaHuman/setup_status.json').write_text(json.dumps(status,indent=2))
(ROOT/'Exports/CharacterLab/README.md').write_text('# Male MetaHuman comparison\n\nThe previous custom male remains in its existing Assets/JinMuWon_v2 files, with a verified snapshot at `'+str(BACKUP)+'`. Its hair, clothing and nail controls are preserved.\n\nNew project: `Unreal/CharacterLab.uproject` (Unreal 5.8). MetaHuman Creator is enabled. Core Data must be installed through Epic Games Launcher before choosing a male preset. No male MetaHuman has been created yet.\n\nTarget: adult lean athletic male; optimized Unreal assembly, with face/body quality assessed before adapting custom hair or clothing.\n')
print(json.dumps(status,indent=2))
