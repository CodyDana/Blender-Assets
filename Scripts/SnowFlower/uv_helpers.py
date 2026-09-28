"""Repair tiny faces flattened by automatic UV projection without deleting them."""
from mathutils import Vector


def repair_collapsed_uv(mesh,epsilon=1e-14):
    mesh.calc_loop_triangles()
    uv=mesh.uv_layers.active.data
    def collapsed():
        bad=set()
        for tri in mesh.loop_triangles:
            a,b,c=(uv[i].uv for i in tri.loops)
            area=abs((b.x-a.x)*(c.y-a.y)-(b.y-a.y)*(c.x-a.x))*.5
            if area<=epsilon:bad.add(tri.polygon_index)
        return bad
    bad=collapsed()
    if not bad:return 0
    # Reserve a narrow strip outside the original islands. Each repaired face
    # has its own non-overlapping cell, so existing texture layout stays valid.
    for loop in uv:loop.uv.x*=.97
    for index,face_index in enumerate(sorted(bad)):
        poly=mesh.polygons[face_index]
        positions=[mesh.vertices[i].co.copy() for i in poly.vertices]
        origin=positions[0]
        edges=[positions[(i+1)%len(positions)]-p for i,p in enumerate(positions)]
        tangent=max(edges,key=lambda e:e.length_squared).normalized()
        normal=poly.normal.normalized();second=normal.cross(tangent).normalized()
        flat=[((p-origin).dot(tangent),(p-origin).dot(second)) for p in positions]
        low=[min(p[k] for p in flat) for k in range(2)]
        span=[max(p[k] for p in flat)-low[k] for k in range(2)]
        if min(span)<=0:raise ValueError(f'Cannot project UV face {mesh.name}:{face_index}')
        for loop_index,p in zip(poly.loop_indices,flat):
            u=(p[0]-low[0])/span[0];v=(p[1]-low[1])/span[1]
            uv[loop_index].uv=(.978+.016*u,(index+.08+.84*v)/len(bad))
    # Nearly collinear boundary corners of long n-gons can still round to a
    # line in float UV storage. Bend only those UV corners inward by a few
    # millionths of the map; the modeled surface and its outline stay intact.
    for attempt in range(4):
        remaining=collapsed()
        if not remaining:break
        for tri in mesh.loop_triangles:
            if tri.polygon_index not in remaining:continue
            values=[uv[i].uv.copy() for i in tri.loops]
            a,b,c=values
            if abs((b.x-a.x)*(c.y-a.y)-(b.y-a.y)*(c.x-a.x))*.5>epsilon:continue
            edge_index=max(range(3),key=lambda k:(values[(k+1)%3]-values[k]).length_squared)
            a=values[edge_index];b=values[(edge_index+1)%3]
            target=(edge_index+2)%3
            delta=b-a;normal=Vector((-delta.y,delta.x)).normalized()
            poly=mesh.polygons[tri.polygon_index]
            center=sum((uv[i].uv for i in poly.loop_indices),Vector((0,0)))/len(poly.loop_indices)
            if normal.dot(center-values[target])<0:normal=-normal
            uv[tri.loops[target]].uv=values[target]+normal*(.000001*(attempt+1))
    remaining=collapsed()
    if remaining:raise ValueError(f'Collapsed UV faces remain in {mesh.name}: {sorted(remaining)}')
    mesh.update()
    return len(bad)
