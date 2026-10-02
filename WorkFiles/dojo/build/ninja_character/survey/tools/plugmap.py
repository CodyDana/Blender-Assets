import json,os,glob,sys,re
ENG=r"C:\Program Files\Epic Games\UE_5.8\Engine"
mod2plug={}
plugs={}
for up in glob.glob(ENG+r"\Plugins\**\*.uplugin",recursive=True):
    try: j=json.load(open(up,encoding='utf-8-sig'))
    except Exception as e: continue
    name=os.path.splitext(os.path.basename(up))[0]
    plugs[name]={'path':up,'EnabledByDefault':j.get('EnabledByDefault',False),'deps':[p['Name'] for p in j.get('Plugins',[])],'beta':j.get('IsBetaVersion',False),'exp':j.get('IsExperimentalVersion',False)}
    for m in j.get('Modules',[]):
        mod2plug[m['Name']]=name
json.dump({'mod2plug':mod2plug,'plugs':plugs},open('plugmap.json','w'),indent=0)
d=json.load(open(sys.argv[1]))
mods=set()
for p,r in d['packages'].items():
    if r.get('status')=='copy': mods|=set(r.get('script_refs',[]))
dojo=json.load(open(r"C:\Users\Cody\Documents\Unreal Projects\DojoLab\DojoLab.uproject"))
den={p['Name'] for p in dojo['Plugins'] if p.get('Enabled')}
def enabled_closure(names):
    out=set(); todo=list(names)
    while todo:
        n=todo.pop()
        if n in out: continue
        out.add(n); todo+= plugs.get(n,{}).get('deps',[])
    return out
allon=enabled_closure(den|{n for n,v in plugs.items() if v['EnabledByDefault']})
for m in sorted(mods):
    pl=mod2plug.get(m)
    print('%-32s %-28s %s'%(m,pl or '(engine module)', '' if not pl else ('ON in DojoLab' if pl in allon else 'NOT ENABLED in DojoLab')))
