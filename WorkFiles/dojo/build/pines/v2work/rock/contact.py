import sys
from PIL import Image
from pathlib import Path
d=Path(sys.argv[1]); names=sys.argv[3:]; out=sys.argv[2]
ims=[Image.open(d/n).convert('RGB') for n in names]
w=sum(i.width for i in ims); h=max(i.height for i in ims)
c=Image.new('RGB',(w,h),(255,255,255)); x=0
for i in ims: c.paste(i,(x,0)); x+=i.width
s=min(1.0, 2400/w); c=c.resize((int(w*s),int(h*s)),Image.LANCZOS); c.save(d/out)
