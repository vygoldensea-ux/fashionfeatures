import numpy as np
from PIL import Image
S=2048
cur=np.array(Image.open('chinfixed.webp').convert('RGB')).astype(np.float32)/255
org=np.array(Image.open('orig/tex.jpeg').convert('RGB').resize((S,S))).astype(np.float32)/255
uv=np.fromfile('0_uv.bin',np.float32).reshape(-1,2); pos=np.fromfile('0_pos.bin',np.float32).reshape(-1,3)
idx=np.fromfile('0_idx.bin',np.uint32).reshape(-1,3)
c=pos[idx].mean(1)
olum=org@[.3,.59,.11]
opur=((org[:,:,2]-org[:,:,1])>0.05)&(olum<0.6)
cpur=((cur[:,:,2]-cur[:,:,1])>0.05)
zone=np.where((c[:,1]>1.38)&(c[:,1]<1.515)&(np.abs(c[:,0])<0.075)&(c[:,2]>-0.03))[0]
restore=np.zeros((S,S),bool); n=0; jaw=[]
for t in zone:
    p=uv[idx[t]]*[S,S]
    x0,y0=np.floor(p.min(0)).astype(int); x1,y1=np.ceil(p.max(0)).astype(int)
    x0,y0=max(x0,0),max(y0,0); x1,y1=min(x1,S-1),min(y1,S-1)
    if x1<x0 or y1<y0 or (x1-x0)*(y1-y0)>40000: continue
    gx,gy=np.meshgrid(np.arange(x0,x1+1)+.5,np.arange(y0,y1+1)+.5)
    (ax,ay),(bx,by),(cx,cy)=p
    d=(by-cy)*(ax-cx)+(cx-bx)*(ay-cy)
    if abs(d)<1e-12: continue
    l1=((by-cy)*(gx-cx)+(cx-bx)*(gy-cy))/d; l2=((cy-ay)*(gx-cx)+(ax-cx)*(gy-cy))/d; l3=1-l1-l2
    ins=(l1>=-0.05)&(l2>=-0.05)&(l3>=-0.05)
    if not ins.sum(): continue
    sl=(slice(y0,y1+1),slice(x0,x1+1))
    if (opur[sl]&ins).sum()/ins.sum()>=0.15: continue   # a real strand in the original
    restore[sl]|=ins&cpur[sl]&~opur[sl]; n+=1; jaw.append(int(t))
print('jaw/underside tris',n,'restored texels',restore.sum())
out=np.where(restore[...,None],org,cur)
Image.fromarray((out*255+.5).clip(0,255).astype(np.uint8)).save('chinfixed2.webp',quality=92,method=6)

np.save('jaw.npy',np.array(jaw))
