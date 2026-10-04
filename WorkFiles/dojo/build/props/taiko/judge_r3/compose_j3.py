from PIL import Image, ImageDraw
S='C:/Users/Cody/AppData/Local/Temp/claude/C--Users-Cody-Desktop-Blender-Projects--claude-worktrees-cardshop-build-integration-5227b4/24ade915-2f01-4a92-a0c7-405f2d922327/scratchpad/ref.png'
ref=Image.open(S).convert('RGB').crop((380,130,660,330))
ours=Image.open('../t3/drum_front_standing_photo.png').convert('RGB')
k=27.5/25.6  # same visible tack diameter
w,h=ours.size; ours=ours.resize((round(w*k),round(h*k)),Image.LANCZOS)
cx=round(512*k); cy=round(183*k)
ours=ours.crop((cx-140,cy-(225-130),cx+140,cy+(330-225)))
s=4
ref=ref.resize((ref.width*s,ref.height*s),Image.LANCZOS); ours=ours.resize((ours.width*s,ours.height*s),Image.LANCZOS)
out=Image.new('RGB',(ref.width*2+20,ref.height+40),'white')
out.paste(ref,(0,40)); out.paste(ours,(ref.width+20,40))
d=ImageDraw.Draw(out)
d.text((10,10),'REFERENCE front centre (band centred, same tack size)',fill='black')
d.text((ref.width+30,10),'OURS t3 drum_front_standing_photo, scaled to the same visible tack diameter',fill='black')
out.save('judge_r3_band_matched.png')
print(out.size)
