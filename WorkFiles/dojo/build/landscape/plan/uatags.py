import sys,re,struct,glob
KEYS=['Dimensions','ImportedSize','Format','SRGB','Triangles','Vertices','ApproxSize','NaniteEnabled','NaniteTriangles','LODs','Materials','CollisionPrims','NumBones','Bones']
def src_size(b):
    i=b.find(b'\x89PNG\r\n')
    if i>0: return 'png %dx%d'%struct.unpack('>II',b[i+16:i+24])
    j=b.find(b'\xff\xd8\xff')
    if j>0:
        k=j+2
        while k<len(b)-9:
            if b[k]!=0xFF: k+=1; continue
            m=b[k+1]
            if m in (0xC0,0xC1,0xC2): 
                h,w=struct.unpack('>HH',b[k+5:k+9]); return 'jpg %dx%d'%(w,h)
            if m in (0xD8,0x01) or 0xD0<=m<=0xD7: k+=2; continue
            L=struct.unpack('>H',b[k+2:k+4])[0]; k+=2+L
    return None
def tags(p):
    b=open(p,'rb').read()
    out={}
    for k in KEYS:
        kb=k.encode()+b'\x00'
        pat=struct.pack('<i',len(kb))+kb
        i=b.find(pat)
        if i<0: continue
        j=i+len(pat)
        n=struct.unpack('<i',b[j:j+4])[0]
        if 0<n<200:
            try: out[k]=b[j+4:j+4+n-1].decode()
            except: pass
    if 'Dimensions' in out or b'TextureSource' in b[:30000]:
        s=src_size(b)
        if s: out['source']=s
    out['MB']=round(len(b)/1e6,1)
    return out
args=[]
for a in sys.argv[1:]: args+= glob.glob(a) if '*' in a else [a]
for p in args:
    t=tags(p)
    if len(t)>1: print(p.replace(chr(92),'/').split('/Content/')[-1], t)
