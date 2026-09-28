import bpy
ob = bpy.data.objects["SF_Blade"]
me = ob.data
mw = ob.matrix_world
vs = [mw @ v.co for v in me.vertices]
zs = sorted(set(round(v.z*1000,1) for v in vs))
import collections
bins = collections.defaultdict(list)
for v in vs:
    bins[round(v.z*1000,0)].append(v)
print("SFSTUDY nz", len(zs))
for z in sorted(bins):
    b = bins[z]
    xs=[v.x*1000 for v in b]; ys=[v.y*1000 for v in b]
    print("SFSTUDY z=%.0f x[%.1f,%.1f] w=%.1f y[%.2f,%.2f] n=%d" % (z,min(xs),max(xs),max(xs)-min(xs),min(ys),max(ys),len(b)))
# pendant, guard lowest points
for n in ["SF_Guard_CentralPendant","SF_Guard_PendantOuterLip","SF_Guard_MainLeafLip","SF_Guard_UnderLeaves","SF_Grip_LowerFerrule","SF_Guard_Wings","SF_Guard_ShoulderEdge"]:
    o=bpy.data.objects.get(n)
    if o: 
        pts=[o.matrix_world@v.co for v in o.data.vertices]
        print("SFSTUDY",n,"zmax",round(max(p.z for p in pts)*1000,1))
print("SFSTUDY origin objects", [ (o.name, tuple(round(c,4) for c in o.location)) for o in bpy.data.objects if o.type=='EMPTY'])
