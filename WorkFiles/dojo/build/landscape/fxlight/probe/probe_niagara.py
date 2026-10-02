import json, unreal
from pathlib import Path
out = {}
names = [n for n in dir(unreal) if 'iagara' in n]
out['classes'] = names
for cls in ('NiagaraSystem','NiagaraEmitter','NiagaraStatelessEmitter','NiagaraComponent','NiagaraEmitterHandle',
            'NiagaraSystemFactoryNew','NiagaraEditorLibrary','NiagaraSystemEditorLibrary','NiagaraFunctionLibrary'):
    c = getattr(unreal, cls, None)
    out[cls] = None if c is None else [m for m in dir(c) if not m.startswith('_')]
ar = unreal.AssetRegistryHelpers.get_asset_registry()
assets = []
for root in ('/Niagara', '/Game'):
    flt = unreal.ARFilter(package_paths=[root], recursive_paths=True, class_paths=[unreal.TopLevelAssetPath('/Script/Niagara', 'NiagaraSystem'), unreal.TopLevelAssetPath('/Script/Niagara', 'NiagaraEmitter')])
    for a in ar.get_assets(flt):
        assets.append(str(a.package_name) + ' ' + str(a.asset_class_path.asset_name))
out['assets'] = assets
Path(r'C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/dojo/build/landscape/fxlight/probe/probe_niagara.json').write_text(json.dumps(out, indent=1))
unreal.log('DJ_STEP_DONE probe_niagara passed=True n=%d' % len(assets))
