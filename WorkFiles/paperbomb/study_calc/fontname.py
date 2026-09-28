import struct, os, json
FONTS={"MasaFont-Bold":r"C:/Users/Cody/Desktop/Blender_Projects/References/Fonts/MasaFont-Bold.ttf",
       "YujiBoku-Regular":r"C:/Users/Cody/Desktop/Blender_Projects/References/Fonts/YujiBoku-Regular.ttf"}
IDS={0:"copyright",1:"family",2:"subfamily",3:"uid",4:"full",5:"version",6:"psname",
     7:"trademark",8:"manufacturer",9:"designer",11:"vendorURL",12:"designerURL",
     13:"license",14:"licenseURL",16:"typoFamily"}
out={}
for n,p in FONTS.items():
    d=open(p,'rb').read()
    _,num=struct.unpack(">IH",d[0:6]); t={}
    for i in range(num):
        o=12+16*i; tag=d[o:o+4].decode('latin-1'); off,ln=struct.unpack(">II",d[o+8:o+16]); t[tag]=(off,ln)
    no=t['name'][0]; fmt,count,so=struct.unpack(">HHH",d[no:no+6])
    rec={}
    for i in range(count):
        e=no+6+12*i
        pid,eid,lid,nid,ln,off=struct.unpack(">HHHHHH",d[e:e+12])
        if nid not in IDS: continue
        raw=d[no+so+off:no+so+off+ln]
        try: s=raw.decode('utf-16-be') if pid==3 or pid==0 else raw.decode('latin-1')
        except Exception: continue
        key=IDS[nid]
        if key not in rec or (lid==0x409 and pid==3): rec[key]=s
    # units per em
    ho=t['head'][0]; upem=struct.unpack(">H",d[ho+18:ho+20])[0]
    rec['unitsPerEm']=upem
    oo=t.get('OS/2')
    if oo:
        cap=struct.unpack(">h",d[oo[0]+88:oo[0]+90])[0] if oo[1]>=96 else None
        rec['sTypoAscender']=struct.unpack(">h",d[oo[0]+68:oo[0]+70])[0]
        rec['sTypoDescender']=struct.unpack(">h",d[oo[0]+70:oo[0]+72])[0]
        rec['sCapHeight']=cap
    out[n]=rec
    print("==",n)
    for k in ("family","subfamily","version","designer","manufacturer","vendorURL","designerURL","license","licenseURL","copyright","trademark","unitsPerEm","sTypoAscender","sTypoDescender"):
        if k in rec: print("   %-12s %s"%(k,str(rec[k])[:260]))
json.dump(out,open("font_names.json","w",encoding="utf-8"),indent=1,ensure_ascii=False)
