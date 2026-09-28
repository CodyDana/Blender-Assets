import json, math
B=json.load(open('ueout/ivB.json')); RAW=json.load(open('ueout/ivB_raw.json'))
REF=B['skeleton']['ref_comp']
def qmul(a,b):
    ax,ay,az,aw=a; bx,by,bz,bw=b
    return [aw*bx+ax*bw+ay*bz-az*by, aw*by-ax*bz+ay*bw+az*bx, aw*bz+ax*by-ay*bx+az*bw, aw*bw-ax*bx-ay*by-az*bz]
def qinv(q): return [-q[0],-q[1],-q[2],q[3]]
worst_tilt=0; worst_head=0; stat=0
for anim,poses in RAW.items():
    for t,P in poses.items():
        for b in P:
            if not b.startswith('stick_') and b!='pivot' : continue
            d=qmul(P[b][3:7], qinv(REF[b][3:7]))
            s=math.sqrt(d[0]**2+d[1]**2+d[2]**2)
            if s>1e-9:
                tilt=math.degrees(math.atan2(math.hypot(d[0],d[1]),abs(d[2])))
                worst_tilt=max(worst_tilt,tilt)
            worst_head=max(worst_head, math.hypot(P[b][0],P[b][1]), abs(P[b][2]-REF[b][2]))
        # front guard static?
        d=qmul(P['stick_00'][3:7], qinv(REF['stick_00'][3:7])); stat=max(stat, math.degrees(2*math.asin(min(1,math.sqrt(d[0]**2+d[1]**2+d[2]**2)))))
print('max stick rotation-axis tilt from rivet axis (deg):', worst_tilt)
print('max stick head off-axis / z drift (cm):', worst_head)
print('stick_00 max rotation over clips (deg):', stat)
# tassel capsule vs fan handle box
box_c=[8.493,-0.1,0.0]; box_h=[21.214/2,1.4/2,1.6515/2]
print('handle box x',box_c[0]-box_h[0],box_c[0]+box_h[0],'y',box_c[1]-box_h[1],box_c[1]+box_h[1],'z',box_c[2]-box_h[2],box_c[2]+box_h[2])
