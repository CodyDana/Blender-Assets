cd /c/Users/Cody/Desktop/Blender_Projects/WorkFiles/dojo/build/hall_armory/ue/checks/ue
DJ_PARTS=routes,flood1v1,floodbr DJ_CEIL=12.46 DJ_OUT=ue_boundary_b.json bash run_ha_ue.sh ha_ue_boundary.py ue_boundary_b.log
DJ_CEIL=12.46 DJ_PARTS=arcs1v1 DJ_OUT=ue_boundary_arcs1v1_b.json bash run_ha_ue.sh ha_ue_boundary.py ue_boundary_arcs1v1_b.log
echo RERUN_DONE
