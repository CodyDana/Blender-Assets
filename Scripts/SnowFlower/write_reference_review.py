"""Create a read-only reference comparison using existing, unaltered images."""
from pathlib import Path
from html import escape
import hashlib

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'WorkFiles/SnowFlower'
ref = '../../References/SnowFlower/SnowFlower_user_reference.png'
render = '../../Renders/SnowFlower/'
rows = [
    ('01', 'Guard construction', 'Major revision',
     'The reference has compact, swept angular shoulders, stepped borders and dense recessed scrollwork. The model has large rounded open loops and an oversized, evenly arranged leaf fan. The lower pointed lacework and decorated transition into the grip are simplified.',
     'Rebuild the outer silhouette and layered backing first. Reduce open loop area, restore angular shoulders, tuck the lateral leaves and add the recessed scrollwork and pointed lower frame. Verify an aligned front silhouette before surface detailing.',
     (805,135,397,377), 'SnowFlower_Guard.png', (150,305,1020,710), (1300,1100)),
    ('02', 'Blade branches and clusters', 'Major revision',
     'The reference has substantial, uneven woody branches with knots, short offshoots and clustered blossoms. The model uses thin, smooth wire-like stems, long diagonal offshoots and small isolated flowers. Some buds read as detached dots. The primary decorative composition does not yet match.',
     'Trace the major cluster locations separately for front and back. Build a tapered irregular trunk with short connected twigs and attached buds. Establish larger focal blossoms and dense clusters before minor filler details; judge their readability at full-sword scale.',
     (807,578,393,275), 'SnowFlower_BladeDetail.png', (425,200,250,480), (1100,1400)),
    ('03', 'Grip wrap and ornament', 'Major revision',
     'The reference wrap is close, flat and visibly crossed, with pebbled leather and connected silver ornament. The model reads as thick padded spiral bands with deep, regular gaps and three isolated floral accents. Two mathematical helices do not produce the same visible interlaced construction.',
     'Flatten the strips and establish readable over-under crossings on the front and side. Reduce raised band edges and deep gaps. Reconstruct the larger connected silver motifs and the shaped lower collar.',
     (949,0,165,180), 'SnowFlower_Pommel.png', (410,0,430,385), (1200,1100)),
    ('04', 'Pommel envelope and engraving', 'Major revision',
     'The model adds prominent front/back flower plates to a broad drum. The reference close-up presents a compact circular cap, recessed flower, concentric borders and dense surrounding engraving. The current model is conspicuously bulkier and emptier around the flower.',
     'Resolve cap orientation against all three reference views, then reduce the projecting plate assembly to the compact envelope. Recess the main flower and reconstruct the concentric rim and ornamental ring. Hidden mounting details remain an interpretation.',
     (807,916,393,268), 'SnowFlower_Pommel.png', (240,250,740,640), (1200,1100)),
    ('05', 'Blossom anatomy and finish', 'Revision required',
     'Repeated smooth oval petals and bead centers make the model look uniform and inflated. Reference flowers have more individual contours, fine center markings, controlled cupping and varied sizes. Broad cloudy metal variation and consistently bright wire borders also differ from the finer worked metal in the sheet.',
     'Match one principal blossom closely, then create controlled variants for the blade, guard and pommel. Use finer petal borders and centers. Compare neutral lighting before changing material values; refine directional grain and localized wear after geometry is corrected.',
     (943,190,127,129), 'SnowFlower_Guard.png', (560,440,320,335), (1300,1100)),
    ('06', 'Tassel and small fittings', 'Revision required',
     'The main cord, charm, bead/cap and bundle are present. The model bundle is narrower and straighter, with a wire-like spread at its ends; it hangs below the guard center, while the reference ends roughly at that level. The charm silhouette, gathered cap, cord texture and knots are simplified.',
     'Match the attachment, charm, cap and bundle endpoints at equal sword height. Increase controlled fullness, refine the gathered cap and braided/knotted appearance, and match the sharper layered charm silhouette. Keep dynamics as a separate game-integration task.',
     (303,26,104,286), 'SnowFlower_Front.png', (466,105,115,363), (900,1600)),
]

intro = ('The current asset is recognizable as the supplied Snow Flower design, but it does not pass a close reference-fidelity review. '
         'The most important gaps are construction and decorative composition, not polygon count. '
         'Previous topology and export checks remain valid; they do not establish design accuracy.')
limits = ('The reference is a concept sheet rather than a dimensioned orthographic specification. '
          'Perspective, view-to-view differences and hidden construction limit certainty. '
          'Absolute dimensions are modeling assumptions. Lighting and backgrounds differ, so exact roughness, color and metalness changes cannot be inferred from these renders alone. '
          'Pommel orientation needs resolution across all views. Comparisons below are detail crops, not registered geometric overlays.')
master = ROOT/'Assets/SnowFlower/SnowFlower_Master.blend'
sha = hashlib.sha256(master.read_bytes()).hexdigest()
md = ['# Snow Flower — detailed reference-fidelity review', '', 'Review date: 2026-09-18. Scope: visual design accuracy of the saved full-detail master against the supplied reference.', '',
      '**Verdict: revisions required before visual sign-off.**', '', intro, '',
      '[Open the illustrated comparison](REFERENCE_REVIEW.html)', '',
      '## What already matches', '',
      '- Long narrow sword, black-and-silver palette, thin blade and gently swept asymmetric point.',
      '- Floral theme, major hilt components, side cord, blossom charm and tassel.',
      '- Broad grip-to-blade relationship. Exact contour and relative widths still need aligned comparison.', '',
      '## Detailed findings and correction order', '']
for num,title,status,finding,repair,*_ in rows:
    md += [f'### {num}. {title} — {status}', '', finding, '', f'**Correction and acceptance criterion:** {repair}', '']
md += ['## Evidence and limits', '', limits, '',
       'Reviewed front, back, side, oblique, guard, blade and pommel renders of the full-detail master. The same primary design is present in the LOD0 export. Low-LOD simplification is not the cause of these discrepancies.', '',
       'Reference: `References/SnowFlower/SnowFlower_user_reference.png`.',
       'Render evidence: `Renders/SnowFlower/SnowFlower_{Front,Back,Side,Oblique,Guard,BladeDetail,Pommel}.png`.',
       f'Master reviewed: `Assets/SnowFlower/SnowFlower_Master.blend`, SHA-256 `{sha}`.', '',
       '## Follow-up checklist', '',
       '- [x] Compare full-detail front/back silhouette and major components against the reference.',
       '- [x] Inspect guard, blade ornament, grip, pommel, floral anatomy, materials and tassel.',
       '- [x] Obtain an independent second visual review and reconcile findings.',
       '- [ ] Match guard silhouette and layered metalwork.',
       '- [ ] Match front/back blade branch hierarchy and floral cluster placement.',
       '- [ ] Rebuild flat crossed grip wrap, connected ornament and lower collar.',
       '- [ ] Resolve and rebuild the compact decorated pommel.',
       '- [ ] Refine blossom variants, silver borders and surface detail.',
       '- [ ] Match tassel silhouette, endpoint and small fittings.',
       '- [ ] Compare revised front/back silhouettes at equal sword height and inspect details under neutral lighting.',
       '- [ ] Re-bake, re-export and repeat relevant structural/export checks after geometry changes.', '',
       'This turn produced a review and correction checklist. No sword geometry, materials or exports were changed. The existing ZIP contains the earlier technical handoff and has not been repackaged for this review.', '']
(OUT/'REFERENCE_REVIEW.md').write_text('\n'.join(md),encoding='utf-8')

def panel(label,path,box,size,height=340):
    vb=' '.join(map(str,box));w,h=size
    return f'<figure><figcaption>{escape(label)}</figcaption><svg viewBox="{vb}" style="height:{height}px" role="img" aria-label="{escape(label)}"><image href="{path}" width="{w}" height="{h}"/></svg></figure>'
cards=[]
for num,title,status,finding,repair,box,name,actual,size in rows:
    cards.append(f'<article><div class="title"><span class="num">{num}</span><h2>{escape(title)}</h2><span class="status">{status}</span></div><div class="pair">'+
                 panel('REFERENCE',ref,box,(1222,1287))+panel('CURRENT FULL-DETAIL MODEL',render+name,actual,size)+
                 f'</div><div class="notes"><p>{escape(finding)}</p><p><b>Required correction:</b> {escape(repair)}</p></div></article>')
html='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Snow Flower — Reference Review</title>
<style>*{box-sizing:border-box}body{margin:0;background:#11171c;color:#e9edf0;font:16px/1.55 system-ui,sans-serif}main{max-width:1160px;margin:auto;padding:46px 28px}h1{font-size:42px;line-height:1.1;margin:10px 0 22px}h2{font-size:21px;margin:0}.eyebrow{color:#aab7c0;text-transform:uppercase;letter-spacing:.15em;font-size:12px}.verdict{border-left:4px solid #f0b977;background:#292821;padding:20px 24px;margin-bottom:24px}.verdict strong{color:#ffd096;font-size:20px}.lede{max-width:980px;color:#c6d0d7}.legend{color:#aab7c0;font-size:14px}article{background:#1b232a;border:1px solid #34414a;border-radius:10px;overflow:hidden;margin:26px 0}.title{display:flex;gap:14px;align-items:center;padding:20px 24px}.num{color:#a6c3d3;font-size:21px}.status{margin-left:auto;color:#ffd096;font-size:13px;border:1px solid #71634e;border-radius:20px;padding:3px 12px}.pair{display:grid;grid-template-columns:1fr 1fr;gap:1px;background:#34414a}figure{margin:0;background:#3e4449;overflow:hidden}figcaption{padding:9px 16px;background:#26313a;color:#d8e4eb;font-size:11px;font-weight:650;letter-spacing:.1em}svg{display:block;width:100%;overflow:hidden}.notes{padding:4px 24px 18px}.notes p:last-child{color:#b6cad7}a{color:#a8d4ef}footer{color:#aab7c0;border-top:1px solid #34414a;margin-top:32px;padding-top:20px}@media(max-width:680px){main{padding:24px 14px}h1{font-size:34px}.pair{grid-template-columns:1fr}.title{flex-wrap:wrap}.status{margin-left:0}}</style>
<main><div class="eyebrow">Snow Flower · Design review · 18 September 2026</div><h1>Recognizable design.<br>Detailed accuracy needs revision.</h1>'''
html+=f'<div class="verdict"><strong>Reference fidelity: revisions required</strong><p>{escape(intro)}</p></div>'
html+='<p class="lede">The long dark blade, silver edge, swept point and floral theme are present. The guard, woody branch motif, grip construction and pommel need the largest changes. The panels below use the original reference and actual full-detail Blender renders.</p><p class="legend">Reference at left · Current model at right · Detail crops have different lighting and viewing angles; they are not registered overlays.</p>'
html+='<article><div class="title"><h2>Overall silhouette and ornament density</h2></div><div class="pair">'+panel('REFERENCE FRONT',ref,(220,3,190,1220),(1222,1287),620)+panel('CURRENT FRONT',render+'SnowFlower_Front.png',(350,75,235,1450),(900,1600),620)+'</div><div class="notes"><p>The reference packs angular guard detail and branch clusters into the silhouette. The current guard has open loops, tiny isolated blade flowers and a longer hanging tassel. Normalize sword height before changing proportions.</p></div></article>'
html+=''.join(cards)+f'<footer><b>Evidence limits</b><p>{escape(limits)}</p><p>No model or export changes were made during this review. Technical export validation remains separate from artistic approval.</p><p><a href="REFERENCE_REVIEW.md">Complete review and correction checklist</a> · <a href="{ref}">Original reference</a> · <a href="{render}SnowFlower_Back.png">Current back view</a> · <a href="{render}SnowFlower_Side.png">Current side view</a></p></footer></main></html>'
(OUT/'REFERENCE_REVIEW.html').write_text(html,encoding='utf-8')
print('Wrote REFERENCE_REVIEW.md and REFERENCE_REVIEW.html; master unchanged:',sha)
