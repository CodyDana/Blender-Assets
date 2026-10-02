"""READ-ONLY inventory of owned scenery content for the dojo LANDSCAPE ROUND (plan stage).

Reads .uasset asset-registry tags (Dimensions, Triangles, NaniteTriangles, ApproxSize, Bones ...) straight from the
package bytes with uatags.py. Opens files for reading only; writes owned_inventory.json next to this script.
Run: py -3 -B scan_owned.py
"""
import glob
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from uatags import tags  # noqa: E402

VAULT = 'C:/ProgramData/Epic/EpicGamesLauncher/VaultCache'
PROJ = 'C:/Users/Cody/Documents/Unreal Projects'
FC = VAULT + '/NordicFi1d739256ce1cV1/data/Content/Fishermans_Cabin'
ST = PROJ + '/Scenery_Tutorial/Content'
CY = VAULT + '/Megaplanb3dc3e6c5a59V1/data/Content/Megaplant_Library/Tree_Japanese_Cypress'
GI = VAULT + '/Megaplan1093c7601c36V1/data/Content/Megaplant_Library/Tree_Ginkgo'
NE = VAULT + '/NiagaraExamplesPack/data/Content/NiagaraExamples'
KA = VAULT + '/ParagonKallari/data/Content/ParagonKallari/FX'
WP = 'C:/Program Files/Epic Games/UE_5.8/Engine/Plugins/Experimental/Water/Content'

GROUPS = {
    'fishermans_trees': [FC + '/Meshes/Foliage/Tree/*.uasset'],
    'fishermans_bushes': [FC + '/Meshes/Foliage/Bush/*.uasset'],
    'fishermans_grass_flowers': [FC + '/Meshes/Foliage/Grass/SM_*.uasset', FC + '/Meshes/Foliage/Flower/SM_*.uasset'],
    'fishermans_rocks': [FC + '/Meshes/Rocks/*.uasset', FC + '/Meshes/Small_Rocks/SM_*.uasset',
                         FC + '/Textures/Rocks/*.uasset', FC + '/Textures/Small_Rocks/*.uasset'],
    'fishermans_mountain_landscape': [FC + '/Meshes/Mountains/*.uasset', FC + '/Meshes/Landscape/*.uasset'],
    'fishermans_foliage_textures': [FC + '/Textures/Foliage/*.uasset', FC + '/Textures/Tiling_Textures/Foliage_Atlas/*.uasset'],
    'fishermans_ground_rock_tiling': [FC + '/Textures/Tiling_Textures/' + d + '/*.uasset' for d in
                                      ('Rock', 'Ground_Grass', 'Ground_Dirt', 'Ground_Dirt_Cracked', 'Water', 'Fog_Cards', 'FX')],
    'scenery_tutorial_megascans': [ST + '/Megascans/Surfaces/*/*.uasset', ST + '/Megascans/3D_Assets/*/*.uasset'],
    'scenery_tutorial_landscape': [ST + '/Landscape/Textures/*.uasset', ST + '/Landscape/Patches/*.uasset'],
    'megaplants_cypress': [CY + '/Tree_Japanese_Cypress_01/Tree_Japanese_Cypress_01_?.uasset', CY + '/Textures/*.uasset'],
    'megaplants_ginkgo': [GI + '/Tree_Ginkgo_01/Tree_Ginkgo_01_?.uasset', GI + '/Textures/*.uasset'],
    'niagara_examples_fog_rock': [NE + '/FX_Fog/T_*.uasset', NE + '/StaticMesh/S_Rock_shopk.uasset',
                                  NE + '/StaticMesh/Rock_shopk/*.uasset'],
    'kallari_water_fx': [KA + '/Textures/Water/*.uasset'],
    'engine_water_plugin': [WP + '/Textures/Foam/*.uasset', WP + '/Textures/Flowmaps/*.uasset',
                            WP + '/Meshes/RiverMesh.uasset'],
}


def main():
    out = {'note': 'read-only asset-registry tags; Dimensions = the texture registry size (the built size; a larger '
                   'source may be capped by MaxTextureSize/LODBias: confirm in-editor before relying on it)',
           'groups': {}}
    for g, pats in GROUPS.items():
        rows = []
        for pat in pats:
            for p in sorted(glob.glob(pat)):
                t = tags(p)
                if len(t) <= 1:
                    continue
                t.pop('source', None)
                t['path'] = p.replace('\\', '/')
                rows.append(t)
        out['groups'][g] = rows
    # Electric Dreams: in the Fab library, download incomplete (stage only)
    ed = VAULT + '/ElectricDreamsSample_5.8'
    staged = 0
    for root, _d, files in os.walk(ed + '/stage'):
        for f in files:
            staged += os.path.getsize(os.path.join(root, f))
    out['electric_dreams'] = {'path': ed, 'data_files': sum(len(f) for _r, _d, f in os.walk(ed + '/data')),
                              'staged_bytes': staged, 'expected_bytes_listings_db': 59982112797,
                              'state': 'download incomplete: nothing extracted under data/, chunks staged since 2026-09-12'}
    with open(os.path.join(HERE, 'owned_inventory.json'), 'w', encoding='utf-8') as fh:
        json.dump(out, fh, indent=1)
    for g, rows in out['groups'].items():
        print(g, len(rows))
    print('electric_dreams', out['electric_dreams']['staged_bytes'] / 1e9, 'GB staged')


if __name__ == '__main__':
    main()
