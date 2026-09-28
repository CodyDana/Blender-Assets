from PIL import Image, ImageDraw
import sys
x0,y0,x1,y1,k=[int(v) for v in sys.argv[1:6]]; name=sys.argv[6]; step=int(sys.argv[7]) if len(sys.argv)>7 else 10
im=Image.open('C:/Users/Cody/Desktop/Blender_Projects/References/Kunai/kunai_reference2.jpg').convert('RGB')
c=im.crop((x0,y0,x1,y1)).resize(((x1-x0)*k,(y1-y0)*k),Image.NEAREST)
d=ImageDraw.Draw(c)
for x in range((x0//step+1)*step,x1,step):
    d.line([((x-x0)*k,0),((x-x0)*k,c.size[1])],fill=(0,255,255) if x%50 else (255,0,255),width=1)
    d.text(((x-x0)*k+2,2),str(x),fill=(255,255,0))
for y in range((y0//step+1)*step,y1,step):
    d.line([(0,(y-y0)*k),(c.size[0],(y-y0)*k)],fill=(0,255,255) if y%50 else (255,0,255),width=1)
    d.text((2,(y-y0)*k+2),str(y),fill=(255,255,0))
c.save(name)
