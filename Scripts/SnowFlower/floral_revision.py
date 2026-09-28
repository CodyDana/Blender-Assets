"""Shared sculpted shallow petals and continuous sculpted relief helpers."""

mat('BranchSteel',(.19,.205,.215),1,.52,1200,.000025)
_sf_bnodes=materials['BranchSteel'].node_tree.nodes
_sf_noise=[n for n in _sf_bnodes if n.type=='TEX_NOISE']
_sf_noise[-1].inputs['Scale'].default_value=1100
for _sf_node in _sf_bnodes:
    if _sf_node.type=='BUMP':
        _sf_node.inputs['Distance'].default_value=.00012
        _sf_node.inputs['Strength'].default_value=.32

def sf_relief_noise(x,seed):
    i=math.floor(x);t=x-i;t=t*t*(3-2*t)
    def h(j):
        value=math.sin(j*127.1+seed*311.7)*43758.5453
        return (value-math.floor(value))*2-1
    return h(i)*(1-t)+h(i+1)*t

def smooth_path(points,steps=5):
    p=list(map(Vector,points));out=[]
    for i in range(len(p)-1):
        a,b,c,d=p[max(0,i-1)],p[i],p[i+1],p[min(len(p)-1,i+2)]
        for j in range(steps):
            t=j/steps
            out.append(.5*((2*b)+(-a+c)*t+(2*a-5*b+4*c-d)*t*t+(-a+3*b-3*c+d)*t*t*t))
    out.append(p[-1]);return out

def relief_branch(name,points,radii,side,group='03_FloralRelief',woody=True):
    """Tapered irregular flattened wood, physically attached to its substrate."""
    pp=smooth_path(points,24 if name.endswith('_Trunk') else 10);v=[];f=[];sides=10;frames=[]
    profile=[(-1,0),(-.76,.16),(-.39,.35),(.10,.66),(.49,.32),(.83,.14),(1,-.03),(.42,-.13),(-.30,-.15),(-.85,-.04)]
    for i,p in enumerate(pp):
        t=i/(len(pp)-1);u=t*(len(radii)-1);j=min(int(u),len(radii)-2)
        rr=radii[j]*(1-(u-j))+radii[j+1]*(u-j)
        tangent=(pp[min(i+1,len(pp)-1)]-pp[max(0,i-1)]).normalized()
        lateral=Vector((tangent.z,0,-tangent.x)).normalized()
        rr*=1+.29*sf_relief_noise(p.z/ .0031,3)+.13*sf_relief_noise(p.z/ .0013,7)
        p=p+lateral*rr*(.27*sf_relief_noise(p.z/.0037,11)+.12*sf_relief_noise(p.z/.0018,21))
        frames.append((p.copy(),lateral.copy(),rr))
        for k in range(sides):
            a,b=profile[k]
            relief=(b+.15)*(1+.16*sf_relief_noise(p.z/.0027,k+1))
            v.append(p+lateral*(rr*a)+Vector((0,side*rr*relief,0)))
        if i:
            for k in range(sides):f.append(((i-1)*sides+k,i*sides+k,i*sides+(k+1)%sides,(i-1)*sides+(k+1)%sides))
    f.extend([tuple(reversed(range(sides))),tuple((len(pp)-1)*sides+k for k in range(sides))])
    add(name,'BranchSteel',group,v,f)
    if woody:
        for q in (-1,1):
            groove=[]
            for i,(p,lat,rr) in enumerate(frames):
                x=q*.24+.095*sf_relief_noise(p.z/.006,19+q)
                for k in range(6):
                    a,b=profile[k];c,d=profile[k+1]
                    if a<=x<=c:
                        ha=(b+.15)*(1+.16*sf_relief_noise(p.z/.0027,k+1))
                        hb=(d+.15)*(1+.16*sf_relief_noise(p.z/.0027,k+2))
                        h=ha+(hb-ha)*(x-a)/(c-a)
                        break
                groove.append(p+lat*rr*x+Vector((0,side*(rr*h-.000015),0)))
            # Interrupted grooves; continuous paired lines looked like metal rails.
            for start in range(3 if q<0 else 11,len(groove)-4,23):
                segment=groove[start:min(start+8,len(groove))]
                rr=radii[0]*(1-start/len(groove))+radii[-1]*start/len(groove)
                tube(name+'_BarkCreases',segment,max(.000050,rr*.06),'Recess',group,4)

def flower(name,center,radius,normal=(0,-1,0),phase=0,group='03_FloralRelief',large=False):
    C=Vector(center);N=Vector(normal).normalized();U=Vector((1,0,0))
    if abs(N.dot(U))>.9:U=Vector((0,1,0))
    U=(U-N*U.dot(N)).normalized();V=N.cross(U).normalized()
    blade=('Blade' in name); count=24 if large else 16
    for k in range(5):
        angle=phase+math.tau*k/5+(.018*math.sin(k*4.3+phase) if blade else 0)
        R=U*math.cos(angle)+V*math.sin(angle);T=N.cross(R)
        length=radius*(1+.038*math.sin(k*2.7+phase));width=radius*(.335 if blade else (.258 if k==0 else .335))
        pc=C+R*length*.52
        outline=[]
        for j in range(count):
            a=math.tau*j/count
            radial=.48*length*math.cos(a)
            # Broad plum petals have a tiny cleft; hilt petals are teardrops.
            if blade:radial-=length*.045*math.exp(-((math.atan2(math.sin(a),math.cos(a))/.23)**2))
            lateral=width*math.sin(a)*(1+.12*math.cos(a))*(1+.025*math.sin(a*3+k))
            if not blade and k==0:lateral*=1-.36*max(0,math.cos(a))
            outline.append((radial,lateral,a))
        verts=[pc+N*radius*.040];faces=[]
        for ring in (1/3,2/3,1):
            for radial,lateral,a in outline:
                height=radius*(.040+.072*ring*ring+.021*math.cos(a)*ring)
                verts.append(pc+R*(radial*ring)+T*(lateral*ring)+N*height)
        for j in range(count):faces.append((0,1+j,1+(j+1)%count))
        for ring in range(2):
            for j in range(count):
                a=1+ring*count+j;b=1+ring*count+(j+1)%count
                faces.append((a,a+count,b+count,b))
        bot=len(verts);verts.append(pc+N*radius*.014)
        base=len(verts)
        for radial,lateral,a in outline:verts.append(pc+R*radial+T*lateral+N*(radius*(.082+.021*math.cos(a))))
        for j in range(count):
            a=1+2*count+j;b=1+2*count+(j+1)%count
            faces.append((a,b,base+(j+1)%count,base+j));faces.append((bot,base+(j+1)%count,base+j))
        add(name+'_Petals','Inlay',group,verts,faces)
        border=[pc+R*r+T*l+N*(radius*(.117+.021*math.cos(a))) for r,l,a in outline]
        tube(name+'_PetalRims',border,radius*.010,'Silver',group,5,True)
        # Fine engraved, branched petal veins only in the inner half.
        for vindex in (-1,0,1):
            line=[]
            for j in range(7):
                t=j/6;rr=radius*(.14+.30*t)
                line.append(C+R*rr+T*(radius*vindex*.047*t*t)+N*radius*(.085-.030*t))
            tube(name+'_PetalEngraving',line,radius*.0034,'Recess',group,4)
    # Metallic center and individual short filaments, without a black hole.
    ellipsoid(name+'_Center',C+N*radius*.125,U*radius*.102,V*radius*.102,N*radius*.065,'Inlay',group,10,5)
    for i in range(9 if large else 7):
        a=math.tau*i/(9 if large else 7)+phase;D=U*math.cos(a)+V*math.sin(a)
        reach=radius*(.17+.035*math.sin(i*2.4));end=C+D*reach+N*radius*.165
        tube(name+'_Filaments',[C+D*radius*.065+N*radius*.12,end],radius*.012,'Silver',group,5)
        ellipsoid(name+'_Stamens',end,U*radius*.028,V*radius*.028,N*radius*.026,'Silver',group,8,4)
