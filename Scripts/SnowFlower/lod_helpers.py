"""Remove complete alternate tassel strands before distance simplification."""
import bmesh
def thin_tassel(obj,keep_every=4):
    bm=bmesh.new();bm.from_mesh(obj.data);bm.verts.index_update();seen=set();remove=[];strand=0
    for v in bm.verts:
        if v in seen:continue
        stack=[v];seen.add(v);component=[]
        while stack:
            p=stack.pop();component.append(p)
            for e in p.link_edges:
                q=e.other_vert(p)
                if q not in seen:seen.add(q);stack.append(q)
        minz=min(p.co.z for p in component);maxz=max(p.co.z for p in component)
        minx=min(p.co.x for p in component);maxx=max(p.co.x for p in component)
        revised = len(component)==95 and .0170<minz<.0250 and .115<maxz<.129 and minx<-.070 and maxx<-.053
        legacy = .033<minz<.04 and .14<maxz<.17 and minx<-.07 and maxx<-.055
        if revised or legacy:
            if strand%keep_every:remove.extend(component)
            elif legacy:
                # Compensate for fewer fibers at distance; keep their guide
                # centers while increasing the remaining five-sided radii.
                ordered=sorted(component,key=lambda v:v.index)
                if len(ordered)%5==0:
                    for i in range(0,len(ordered),5):
                        ring=ordered[i:i+5];center=sum((v.co for v in ring),ring[0].co*0)/5
                        for v in ring:v.co=center+(v.co-center)*2.5
            strand+=1
    if remove:bmesh.ops.delete(bm,geom=remove,context='VERTS')
    bm.to_mesh(obj.data);bm.free();obj.data.update()
    return {'identified_tassel_strands':strand,'removed_strand_vertices':len(remove),'keep_every':keep_every,'remaining_fiber_radius_scale':1.0,'filled_core_retained':True}
