import json,re,csv,statistics as S,sys
from pathlib import Path
def files(d):
    g=open(d+"/game_perf_guard.txt",encoding="utf-8-sig").read(); g=g[g.rfind("started pid="):]
    return sorted({Path(m.group(1)) for m in re.finditer(r" csv (.+?\.csv) \d+", g)}, key=lambda p:p.name)
def load(f):
    allr=list(csv.reader(open(f,encoding="utf-8",errors="replace")))
    hdr=max([r for r in allr if r and r[0]=="EVENTS"],key=len)
    rows=[r+[""]*(len(hdr)-len(r)) for r in allr if r and r[0]!="EVENTS" and not r[0].startswith("[") and len(r)<=len(hdr)][3:]
    out={}
    for i,h in enumerate(hdr):
        x=[]
        for r in rows:
            try: x.append(float(r[i]))
            except ValueError: pass
        if x: out[h]=S.mean(x)
    return out
da,ia,db,ib=sys.argv[1],int(sys.argv[2]),sys.argv[3],int(sys.argv[4])
a=load(files(da)[ia]); b=load(files(db)[ib])
d=sorted(((b.get(k,0)-a.get(k,0),k,round(a.get(k,0),3),round(b.get(k,0),3)) for k in set(a)|set(b) if not k.startswith("GPU/")),reverse=True)
for x in d[:22]: print(round(x[0],3),x[1],x[2],x[3])
