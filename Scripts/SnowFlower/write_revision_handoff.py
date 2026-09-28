"""Write current revision handoff from measured validation reports."""
from pathlib import Path
import json,hashlib
from html import escape
root=Path(__file__).resolve().parents[2];work=root/'WorkFiles/SnowFlower';out=root/'Exports/SnowFlower'
audit=json.loads((work/'audit_report.json').read_text());exp=json.loads((out/'export_report.json').read_text());visual=json.loads((work/'lod_visual_report.json').read_text())
sha=hashlib.sha256((root/'Assets/SnowFlower/SnowFlower_Master.blend').read_bytes()).hexdigest()
assert sha==audit['source_sha256']==exp['source_sha256']==visual['source_sha256']
assert audit['status']=='NO_CHECKED_STRUCTURAL_DEFECTS_FOUND' and exp['status']=='passed'
assert set(exp['lods'])==set(visual['lods'])=={'0','1','2'}
assert len(exp['roundtrips'])==6 and all(v['uvs_present'] and v['no_degenerate_faces_or_loose_vertices'] for v in exp['roundtrips'].values())
assert all(v['all_images_loaded'] and v['bounds_error_m']<1e-6 for v in visual['lods'].values())
tot=audit['totals'];b=audit['overall_bounds_world']['size'];mats=json.loads((out/'material_manifest.json').read_text())['materials'];textures=list((out/'Textures').glob('*.png'))
pommel=[v['bounds_world'] for name,v in audit['objects'].items() if name.startswith('SF_Pommel_')]
pommel_size=[max(v['max'][i] for v in pommel)-min(v['min'][i] for v in pommel) for i in range(3)]
changes=[
('Guard','Manually placed reference landmarks define lower curved shoulders and narrower upright cupped leaves. Shorter thorn lace exposes the large dark central pendant. A seated raised crown and compact branch lattice frame the upper flower.'),
('Blade relief','Varied branch routing and blossom groups, integrated woody swellings, increased local contour variation and made bark engraving visible on the relief surface. Retained proximal blossom clusters and the second group near 61–65% of blade length.'),
('Flowers','Rebuilt petals as shallow cupped surfaces with varied contours, thinner rims, fine inner engraving and metallic stamen centers.'),
('Grip','Replaced the padded spiral with thin alternating over/under strips whose crossings face front and back. Added connected floral ornament and finer collar scrollwork.'),
('Pommel',f'Rebuilt as one rounded housing with its axis along Blender Y, measuring {pommel_size[0]*1000:.2f} mm across and {pommel_size[1]*1000:.2f} mm deep including relief. Recessed flowers decorate the front and back. Rounded shoulders fill the side silhouette and seat into the grip.'),
('Tassel','Added braided cord and tied knots, a layered charm, a fuller curved bundle, staggered strand tips and loose edge fibers. Shortened the endpoint to approximately guard height.'),
('Steel and presentation','Added subtle lengthwise tool marks to the dark steel and bevel. Added pommel illumination, reduced broad material cloudiness, and corrected camera near clipping for close-up inspection.')]
limits=('Exact identity with the reference has not been established. '
        'Fine thornwork, flower engraving and small branch details are reconstructed rather than exact tracings. '
        'The wheel pommel reconciles the front, back and side silhouettes; its ornamental surface detail remains interpretive. '
        'Hidden geometry is inferred, and reference lighting and perspective cannot be recovered exactly from this sheet.')
lodrows='\n'.join(f"| LOD{k} | {v['triangles']:,} | [FBX](SM_SnowFlower{'' if k=='0' else '_LOD'+k}.fbx) | [GLB](SM_SnowFlower{'' if k=='0' else '_LOD'+k}.glb) |" for k,v in exp['lods'].items())
readme=f'''# Snow Flower — design revision 3

Updated from the detailed reference review, with a further pass on guard landmarks, branch surface detail and the wheel pommel. Revision 2 work on the cupped blossoms, crossed grip wrap, connected hilt ornament and curved tassel is retained. Editable source has {tot['mesh_objects']} component meshes and {tot['triangles']:,} triangles. See [revision review](../../WorkFiles/SnowFlower/REFERENCE_REVIEW.md) and [illustrated comparison](../../WorkFiles/SnowFlower/REFERENCE_REVIEW.html).

## Files

- [SnowFlower_Master.blend](../../Assets/SnowFlower/SnowFlower_Master.blend): editable components and procedural materials.
- [SnowFlower_Game.blend](../../Assets/SnowFlower/SnowFlower_Game.blend): consolidated LOD0 with packed baked textures and collision meshes.
- FBX/GLB exports below contain revision 3. Use `SnowFlower_DesignRevision3.zip` for this update. Previous `SnowFlower_Package.zip` and `SnowFlower_ReferenceRevision.zip` archives remain snapshots of their earlier revisions.

| Detail | Visible triangles | FBX | GLB |
| --- | ---: | --- | --- |
{lodrows}

LOD0 is the heavy close-up source. Reduced versions preserve fewer fine ornamental faces; their screen-size transitions and performance need testing in the game. Triangle counts exclude collision objects.

## Scale and attachment

Measured bounds: **{b[0]:.6f} × {b[1]:.6f} × {b[2]:.6f} m**, including tassel and pommel. The origin remains the grip center. The blade extends along Blender local +Z; FBX is Z-up and GLB uses the standard Y-up conversion.

Only LOD0 FBX contains three `UCX_SM_SnowFlower_00/01/02` convex collision objects. They approximate the rigid sword and exclude the tassel. Collision behavior and hand sockets still require setup in Unreal.

## Textures

{len(textures)} PNG files cover {len(mats)} materials, including the new BranchSteel material. Exact hookups are in [material_manifest.json](material_manifest.json).

- BaseColor: sRGB.
- Normal: linear/non-color, OpenGL +Y. Enable Flip Green Channel for Unreal/DirectX.
- Roughness: linear grayscale.
- ORM: linear; R=1 (no baked AO), G=roughness, B=metallic. Use either standalone roughness or ORM.G.

The GLBs contain their textures. Check or recreate FBX material hookups in Unreal. The Blender game file has packed textures.

## Validation and limits

The master passed structural checks without reported degenerate/nonmanifold/loose geometry or UV defects. All six exports passed Blender reimport checks for expected triangle count, UV presence, and absence of degenerate faces/loose vertices. Imported GLBs were rendered with their own materials; texture loading and bounds checks passed.

{limits}

The tassel is static. No Unreal runtime, attachment, collision behavior, LOD-switching or performance test has been performed.
'''
(out/'README.md').write_text(readme,encoding='utf-8')
review='# Snow Flower — design revision 3 review\n\n**Status: geometry and exports updated; exact visual identity is not established.**\n\n'
review+='[Open reference / revision 1 / current comparisons](REFERENCE_REVIEW.html)\n\n## Changes made\n\n'
review+='\n'.join(f'- **{name}:** {desc}' for name,desc in changes)
review+=f'\n\n## Remaining limits\n\n{limits}\n\nThe tassel remains static. Unreal import, material hookups, hand attachment, collision behavior, LOD transitions and runtime performance still require testing.\n\n## Verification\n\n- {tot["mesh_objects"]} editable mesh objects; {tot["triangles"]:,} source triangles; {len(mats)} materials.\n- Source structural audit: {audit["status"]}.\n- Six FBX/GLB reimports passed; exported GLBs rendered with their own material textures.\n- Master SHA-256: `{sha}`.\n- No character assets or existing Blender GUI sessions were altered.\n\nRevision 1 source and renders are preserved locally in `WorkFiles/SnowFlower/Revision1`. Previous ZIP archives remain unchanged; the current package is `SnowFlower_DesignRevision3.zip`.\n'
(work/'REFERENCE_REVIEW.md').write_text(review,encoding='utf-8')
(work/'QA_NOTES.md').write_text('# Snow Flower — revision 3 QA\n\n'+review.split('## Changes made',1)[1]+'\n\nUnderlying evidence: `audit_report.json`, `lod_visual_report.json`, `Exports/SnowFlower/export_report.json`. Separate intersecting ornament shells are intentional and are not certified by the topology audit as a unioned solid.\n',encoding='utf-8')
plan='''# Snow Flower — current checklist

## Retained revision 2 work

- [x] Preserve revision 1 source and comparison renders.
- [x] Replace guard silhouette and layered metalwork.
- [x] Recompose blade clusters and revise branch relief.
- [x] Rebuild shallow blossoms and engraved details.
- [x] Rebuild flat crossed wrap and connected hilt ornament.
- [x] Match tassel endpoint and improve strand density/shape.
- [x] Retain close-up lighting and camera clipping corrections.

## Revision 3 implementation and verification

- [x] Place guard landmarks against the reference: lower curved shoulders and narrower upright cupped leaves.
- [x] Shorten thorn lace and expose the large dark central pendant.
- [x] Increase local branch variation and make bark engraving visible on the branch surface.
- [x] Replace the angled pommel with one rounded housing on the Y axis and increase its depth to match the grip in side view.
- [x] Match front and rear pommel flowers and reconcile front/back/side silhouettes.
- [x] Review actual current front, back, side and detail renders against the reference.
- [x] Run the updated structural audit.
- [x] Re-bake materials and export three FBX/GLB detail levels.
- [x] Reimport exports and render them with their own materials.

## Acceptance limits and later integration

- [ ] Exact design identity: not established. Fine thornwork, engraving and branch details remain reconstructed; hidden geometry is inferred.
- [ ] Unreal import, material hookups, hand attachment and collision behavior.
- [ ] LOD switching/performance against the actual camera and platform.
- [ ] Dynamic tassel rig or simulation, if required.

See `REFERENCE_REVIEW.md` for current findings. Checked implementation tasks record work completed, not a claim of identical reference fidelity.
'''
(work/'REVIEW_PLAN.md').write_text(plan,encoding='utf-8')
(work/'PACKAGE_README.md').write_text('''# Snow Flower — design revision 3

Start with `Exports/SnowFlower/README.md` for models, texture conventions, measured scale, LOD counts and integration limits.

- `Assets/SnowFlower/`: editable master and consolidated game Blender files.
- `Exports/SnowFlower/`: revised FBX/GLB files and baked PNG textures.
- `Renders/SnowFlower/`: actual current Blender renders, including imported exports.
- `References/SnowFlower/`: unchanged user-supplied reference.
- `WorkFiles/SnowFlower/`: current QA, checklist and illustrated comparison.
- `WorkFiles/SnowFlower/Revision1/Renders/`: selected previous renders for comparison.
- `Scripts/SnowFlower/`: reproducible Blender construction, baking and export code. Update hard-coded ROOT paths before running elsewhere; generation overwrites asset outputs. Blender 5.2 was used.

Revision 3 adjusts the guard from reference landmarks, increases branch surface variation and visible engraving, and replaces the angled pommel with one wheel bearing matching front and rear flowers. Existing revision 2 work on blossoms, crossed grip wrap, hilt ornament and the curved tassel is retained.

Exact reference identity is not established. Fine engravings are reconstructed and hidden geometry is inferred. The tassel is static and Unreal runtime testing remains outstanding. This archive is SnowFlower_DesignRevision3.zip; earlier ZIP archives remain unchanged.

Every entry was checked against the SHA-256 hashes in PACKAGE_MANIFEST.json after packaging.
''',encoding='utf-8')

def panel(label,path,box,size,height=350):
    return f'<figure><figcaption>{escape(label)}</figcaption><svg viewBox="{" ".join(map(str,box))}" style="height:{height}px" role="img" aria-label="{escape(label)}"><image href="{path}" width="{size[0]}" height="{size[1]}"/></svg></figure>'
ref='../../References/SnowFlower/SnowFlower_user_reference.png';current='../../Renders/SnowFlower/';old='Revision1/Renders/'
html='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Snow Flower — Design Revision 3</title><style>*{box-sizing:border-box}body{margin:0;background:#11171d;color:#e7edf1;font:16px/1.6 system-ui,sans-serif}main{max-width:1420px;margin:auto;padding:36px 24px}h1{font-size:38px;margin:0 0 18px}h2{font-size:23px;margin:0;padding:16px 22px}.notice{background:#2c2922;border-left:4px solid #cfac76;padding:18px 24px}.lede{color:#bbcbd5}.grid{display:grid;grid-template-columns:repeat(3,1fr);gap:2px;background:#3a4852}article{border:1px solid #3a4852;margin:26px 0;border-radius:9px;overflow:hidden;background:#1b242c}figure{margin:0;overflow:hidden;background:#485059}figcaption{background:#26343f;padding:8px 14px;font-size:11px;letter-spacing:.08em}svg{display:block;width:100%;overflow:hidden}.notes{padding:0 22px 10px;color:#c2d0d9}a{color:#a7d4ef}@media(max-width:850px){.grid{grid-template-columns:1fr}main{padding:20px 12px}}</style><main><h1>Snow Flower · Design revision 3</h1><p class="lede">User reference / preserved revision 1 / current revision 3. Model images are actual Blender renders. Lighting and crop angles differ.</p>'''
html+=f'<div class="notice">{escape(limits)}</div>'
cases=[('Overall design',(218,0,190,1220),'SnowFlower_Front.png',(350,75,235,1450),(350,60,235,1470),(900,1600),620,changes[1][1]),
('Guard',(805,135,397,377),'SnowFlower_Guard.png',(150,305,1020,710),(140,340,1050,620),(1300,1100),350,changes[0][1]),
('Blade relief',(807,578,393,275),'SnowFlower_BladeDetail.png',(425,200,250,480),(425,200,250,480),(1100,1400),350,changes[1][1]),
('Pommel',(807,916,393,268),'SnowFlower_Pommel.png',(240,250,740,640),(240,250,740,640),(1200,1100),350,changes[4][1])]
for title,rb,name,ob,nb,size,height,desc in cases:
    html+=f'<article><h2>{title}</h2><div class="grid">'+panel('REFERENCE',ref,rb,(1222,1287),height)+panel('REVISION 1',old+name,ob,size,height)+panel('CURRENT — REVISION 3',current+name,nb,size,height)+f'</div><div class="notes"><p>{escape(desc)}</p></div></article>'
html+='<p><a href="REFERENCE_REVIEW.md">Current review</a> · <a href="../../Exports/SnowFlower/README.md">Asset handoff</a> · <a href="../../Renders/SnowFlower/SnowFlower_Back.png">Current back view</a></p></main></html>'
(work/'REFERENCE_REVIEW.html').write_text(html,encoding='utf-8')
print(json.dumps({'status':'handoff_updated','revision':3,'source_sha256':sha,'triangles':tot['triangles'],'materials':len(mats),'textures':len(textures)}))
