"""Extract Epic's embedded preview images for local preset selection."""
from pathlib import Path
from io import BytesIO
from PIL import Image,ImageDraw,ImageFont
import re,json
ROOT=Path(r'C:\Users\Cody\Desktop\Blender_Projects')
SOURCE=Path(r'C:\Program Files\Epic Games\UE_5.8\Engine\Plugins\MetaHuman\MetaHumanCharacter\Content\Optional\Presets')
OUT=ROOT/'WorkFiles/MetaHuman/preset_thumbnails';OUT.mkdir(parents=True,exist_ok=True)
report={}
for path in sorted(SOURCE.glob('*.uasset')):
    data=path.read_bytes();images=[]
    for match in re.finditer(b'\x89PNG\r\n\x1a\n|\xff\xd8\xff',data):
        try:
            im=Image.open(BytesIO(data[match.start():]));im.load()
            if min(im.size)<128 or max(im.size)>2048:continue
            file=OUT/(path.stem+'_'+str(len(images))+'.png');im.convert('RGB').save(file)
            images.append({'file':str(file),'size':im.size,'offset':match.start()})
        except Exception:continue
    report[path.stem]=images
(OUT/'images.json').write_text(json.dumps(report,indent=2))
names=[n for n,imgs in report.items() if imgs]
sheet=Image.new('RGB',(7*180,((len(names)+6)//7)*212),(32,32,32));d=ImageDraw.Draw(sheet)
font=ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',18)
for i,n in enumerate(names):
    im=Image.open(report[n][0]['file']);im.thumbnail((176,180))
    x=(i%7)*180;y=(i//7)*212;sheet.paste(im,(x,y));d.text((x+5,y+184),n,font=font,fill='white')
sheet.save(OUT/'PresetSheet.png')
print(json.dumps({n:len(imgs) for n,imgs in report.items()}))
