from pathlib import Path
import unreal,json
classes=[unreal.MaterialEditingLibrary,unreal.SkeletalMesh,unreal.SkeletalMeshEditorSubsystem,unreal.MaterialInstanceDynamic,unreal.MaterialExpressionTextureSampleParameter2D,unreal.FbxSkeletalMeshImportData,unreal.Texture2D]
out={}
for c in classes:
    out[c.__name__]={}
    for n in dir(c):
        if not n.startswith('_') and any(t in n for t in ['lod','triang','param','sample','compile','texture','alpha','srgb','normal','skeletal','material']):
            try: out[c.__name__][n]=str(getattr(c,n).__doc__)
            except: pass
Path(r'C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/BlackNunchucks/RecolorUnreal/api_probe.json').write_text(json.dumps(out,indent=2))
