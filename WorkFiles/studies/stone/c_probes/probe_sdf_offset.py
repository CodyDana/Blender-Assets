import bpy, bmesh, json, sys, time
from mathutils import Vector
for _o in list(bpy.data.objects): bpy.data.objects.remove(_o)
out={}; sc=bpy.context.scene
bm=bmesh.new(); bmesh.ops.create_cube(bm,size=1.0); me=bpy.data.meshes.new("c"); bm.to_mesh(me); bm.free()
o=bpy.data.objects.new("c",me); sc.collection.objects.link(o)
def grp(offs, vox, band):
    ng=bpy.data.node_groups.new("g","GeometryNodeTree")
    ng.interface.new_socket("Geometry",in_out="INPUT",socket_type="NodeSocketGeometry")
    ng.interface.new_socket("Geometry",in_out="OUTPUT",socket_type="NodeSocketGeometry")
    N=ng.nodes; L=ng.links; gi=N.new("NodeGroupInput"); go=N.new("NodeGroupOutput")
    m=N.new("GeometryNodeMeshToSDFGrid"); m.inputs["Voxel Size"].default_value=vox; m.inputs["Band Width"].default_value=band
    L.new(gi.outputs[0],m.inputs["Mesh"]); cur=m.outputs[0]
    for d in offs:
        n=N.new("GeometryNodeSDFGridOffset"); n.inputs["Distance"].default_value=d; L.new(cur,n.inputs["Grid"]); cur=n.outputs[0]
    g=N.new("GeometryNodeGridToMesh"); out.setdefault("g2m_default_threshold", g.inputs["Threshold"].default_value); g.inputs["Threshold"].default_value=0.0; L.new(cur,g.inputs["Grid"]); L.new(g.outputs[0],go.inputs[0]); return ng
for offs,band in (((),3),((0.05,),10),((-0.05,),10),((-0.1,0.1),20),((0.1,-0.1),20),((-0.03,0.03),6)):
    ob=o.copy(); ob.data=o.data.copy(); sc.collection.objects.link(ob)
    md=ob.modifiers.new("gn","NODES"); md.node_group=grp(offs,0.01,band)
    dg=bpy.context.evaluated_depsgraph_get(); dg.update(); eo=ob.evaluated_get(dg)
    vs=[v.co for v in eo.data.vertices]
    key=f"{offs}_band{band}"
    if vs:
        dims=[round(max(v[i] for v in vs)-min(v[i] for v in vs),3) for i in range(3)]
        # corner rounding: distance of the farthest vertex from centre along (1,1,1)
        dmax=max(v.dot(Vector((1,1,1)).normalized()) for v in vs)
        out[key]={"dims":dims,"diag_extent":round(dmax,3),"faces":len(eo.data.polygons)}
    else: out[key]="empty"
out["cube_diag_extent_sharp"]=round(0.5*3**0.5,3)
json.dump(out,open(sys.argv[-1],"w"),indent=1)
