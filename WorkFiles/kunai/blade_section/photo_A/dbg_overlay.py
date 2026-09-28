from PIL import Image, ImageDraw
import numpy as np, json
im=Image.open('C:/Users/Cody/Desktop/Blender_Projects/References/Kunai/kunai_reference2.jpg')
fits=json.load(open('blade_lines.json'))
x0,y0,x1,y1=250,100,410,200; s=6
c=im.crop((x0,y0,x1,y1)).resize(((x1-x0)*s,(y1-y0)*s),Image.NEAREST)
d=ImageDraw.Draw(c)
T=lambda x,y:((x-x0+0.5)*s,(y-y0+0.5)*s)
cols={'top_front':(255,0,0),'ridge_front':(0,255,0),'bot_front':(255,0,255),'bot_rear':(255,255,0),'ridge_rear':(0,255,255),'top_rear':(255,128,0)}
for k,f in fits.items():
    for (x,y),kp in zip(f['pts'],f['keep']):
        X,Y=T(x,y); d.ellipse([X-2,Y-2,X+2,Y+2],fill=cols[k] if kp else (0,0,0))
    cc=np.array(f['c']); dd=np.array(f['d'])
    a=cc-dd*120; b=cc+dd*120
    d.line([T(*a),T(*b)],fill=cols[k],width=1)
c.save('dbg_lines.png')
