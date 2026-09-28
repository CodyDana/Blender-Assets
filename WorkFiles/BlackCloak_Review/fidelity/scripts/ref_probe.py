import sys,os; sys.path.insert(0,os.path.dirname(__file__))
from imgutil import *
a=load(r"C:/Users/Cody/Desktop/Blender_Projects/References/BlackCloak/blackcloak.png")
print("shape",a.shape, a[...,3].min())
L=lum(a)*255
for t in (200,220,235,245):
    m=L<t; ys,xs=np.nonzero(m); print(t,"bbox x",xs.min(),xs.max(),"y",ys.min(),ys.max(),"area",m.sum())
print("corners",L[:5,:5].mean(),L[-5:,-5:].mean(), L[0].mean(), L[-1].mean())
hist=np.histogram(L,bins=[0,20,30,40,50,60,70,80,100,150,200,240,256])
print(hist)
