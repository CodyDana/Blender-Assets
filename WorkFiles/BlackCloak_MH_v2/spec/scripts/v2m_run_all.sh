#!/usr/bin/env bash
# Full BlackCloak_MH_v2 measurement round on the SHIPPED FBX (Git Bash). Each step is one headless Blender call
# (< 8 min each). Usage:
#   bash v2m_run_all.sh <out_dir> [<fbx>] [step ...]
# steps (default all, in order): geom photo photo_body jin views resim settled blind
# Everything lands in <out_dir>; the blind key goes to the scratchpad path in $V2M_BLIND_KEY (required for 'blind').
set -u
B="C:/Program Files/Blender Foundation/Blender 5.2/blender.exe"
S="C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/BlackCloak_MH_v2/spec/scripts"
OUT="$1"; shift
FBX="${1:-C:/Users/Cody/Desktop/Blender_Projects/Exports/Garments/BlackCloak_MH_v2/SK_BlackCloak_MH_v2.fbx}"; [ $# -gt 0 ] && shift
STEPS="${*:-geom photo photo_body jin views resim settled blind}"
mkdir -p "$OUT/logs"
run() { local name="$1"; shift; echo "== $name"; timeout 470 "$B" -b --factory-startup --python "$@" > "$OUT/logs/$name.log" 2>&1; echo "   exit $? ($(grep -c Traceback "$OUT/logs/$name.log") tracebacks)"; grep -E "^V2M" "$OUT/logs/$name.log" | cut -c1-400; }
for st in $STEPS; do case $st in
  geom)       run geom "$S/v2m_geom_check.py" -- --fbx "$FBX" --out "$OUT/geom.json" ;;
  photo)      run render_photo "$S/v2m_render.py" -- --view photo --fbx "$FBX" --body 0 --mult 3 --samples 256 --out "$OUT" --tag photo
              run sil_photo "$S/v2m_silhouette_score.py" -- "$OUT" photo
              run fab_photo "$S/v2m_fabric_score.py" -- "$OUT" photo ;;
  photo_body) run render_photo_body "$S/v2m_render.py" -- --view photo --fbx "$FBX" --body 1 --mult 2 --no-beauty --out "$OUT" --tag photo_body
              run sil_photo_body "$S/v2m_silhouette_score.py" -- "$OUT" photo_body ;;
  jin)        run render_jin "$S/v2m_render.py" -- --view jin --fbx "$FBX" --body 1 --samples 256 --out "$OUT" --tag jin
              run jin_score "$S/v2m_jin_score.py" -- "$OUT" jin
              run render_face "$S/v2m_render.py" -- --view face --fbx "$FBX" --body 1 --samples 256 --out "$OUT" --tag face ;;
  views)      for v in front q34 q34_other side_r side_l back; do run render_$v "$S/v2m_render.py" -- --view $v --fbx "$FBX" --body 1 --samples 160 --out "$OUT" --tag $v; done
              run render_hem "$S/v2m_render.py" -- --view hem --fbx "$FBX" --body 0 --samples 256 --out "$OUT" --tag hem ;;
  resim)      run resim_a "$S/v2m_posed_resim.py" -- --fbx "$FBX" --out "$OUT/resim" --poses idle,apose
              run resim_b "$S/v2m_posed_resim.py" -- --fbx "$FBX" --out "$OUT/resim_b" --poses long_stride,arms_forward,deep_crouch,arms_up ;;
  settled)    run sil_idle "$S/v2m_silhouette_score.py" -- "$OUT/resim" idle_photo - "$OUT/photo_silhouette.json"
              run sil_apose "$S/v2m_silhouette_score.py" -- "$OUT/resim" apose_photo ;;
  blind)      run blind "$S/v2m_make_blind.py" -- "$OUT" photo "$OUT/blind" "${V2M_BLIND_KEY:?set V2M_BLIND_KEY to a scratchpad json path}" ;;
  *) echo "unknown step $st" ;;
esac; done
