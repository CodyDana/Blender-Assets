#!/bin/bash
D="C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/BlackCloak_Review/male/blender"
B="C:/Program Files/Blender Foundation/Blender 5.2/blender.exe"
while read -r tag view body pose mat mult samp; do
  [ -z "$tag" ] && continue
  if [ -f "$D/renders/$tag.json" ]; then echo "skip $tag"; continue; fi
  echo "START $tag $(date +%T)"
  "$B" -b "$D/male_cloak_scene.blend" --factory-startup --python "$D/scripts/render_view.py" -- $tag $view $body $pose $mat $mult $samp > "$D/logs/render_$tag.log" 2>&1
  grep -q "^INFO" "$D/logs/render_$tag.log" && echo "OK $tag $(date +%T)" || echo "FAIL $tag"
done <<LIST
a_ref_cloak_game ref 0 rest game 4 256
a2_ref_cloak_tiled ref 0 rest tiled 4 256
b_ref_body_down_game ref 1 down game 4 256
b2_ref_body_rest_game ref 1 rest game 2 256
d_front_body_down_game front 1 down game 2 256
d_q34_body_down_game q34 1 down game 2 256
d_q34other_body_down_game q34_other 1 down game 2 256
d_side_r_body_down_game side_r 1 down game 2 256
d_side_l_body_down_game side_l 1 down game 2 256
d_back_body_down_game back 1 down game 2 256
d_back_body_rest_game back 1 rest game 2 256
d_front_cloak_game front 0 rest game 2 256
e_macro_mantle_game macro_mantle 0 rest game 2 256
e_macro_mantle_tiled macro_mantle 0 rest tiled 2 256
e_macro_panel_game macro_panel 0 rest game 2 256
e_macro_panel_tiled macro_panel 0 rest tiled 2 256
LIST
echo ALLDONE
