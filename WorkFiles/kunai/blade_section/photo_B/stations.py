import numpy as np, json
Ls=json.load(open('blade_lines.json'))
Tt,Tb,tip,R,Rc,M=np.load('keypts.npy')
def line(k): return np.array(Ls[k]['c']),np.array(Ls[k]['d'])
def hit(P,v,k):  # intersect ray P + t v with line k, return t
    c,d=line(k); A=np.column_stack([v,-d]); t=np.linalg.solve(A,c-P); return t[0]
for chord_ang in (67.24, 90-23.21+0*0, 90-20.83):
    v=np.array([np.cos(np.radians(chord_ang)),np.sin(np.radians(chord_ang))])*-1  # pointing up-left toward top edge
    ax=np.array([np.cos(np.radians(chord_ang-90)),np.sin(np.radians(chord_ang-90))])  # along blade toward tip
    # shoulder point: where top_rear meets grip ~ measure along axis
    print('chord ang',chord_ang)
    rows=[]
    for xs in np.arange(262,400,6):
        # station point on a reference line through M along ax
        P=M+((xs-M[0])/ax[0])*ax
        front = P@ax >= M@ax
        tt=hit(P,v,'top_front' if front else 'top_rear'); tb=hit(P,v,'bot_front' if front else 'bot_rear')
        tr=hit(P,v,'ridge_front' if front else 'ridge_rear')
        mid=(tt+tb)/2; hw=(tt-tb)/2; q=(tr-mid)/hw
        rows.append((xs,hw,tr-mid,q))
        print(f"  x={xs:5.1f} halfw={hw:6.2f} ridge_off={tr-mid:6.2f}px q={q:6.3f}")
