import numpy as np, sys
from PIL import Image
S=2048
cur=np.array(Image.open(sys.argv[1]).convert('RGB'))
pre=np.array(Image.open('pre/tex.webp').convert('RGB'))
uv=np.fromfile('0_uv.bin',np.float32).reshape(-1,2); pos=np.fromfile('0_pos.bin',np.float32).reshape(-1,3)
idx=np.fromfile('0_idx.bin',np.uint32).reshape(-1,3)
c=pos[idx].mean(1); vy=pos[idx][:,:,1]
# everything that is not the head: shoulders, chest, back, arms (any corner below the jaw line, or wide of the face)
body=np.where((vy.max(1)<1.45)|((np.abs(c[:,0])>0.10)&(c[:,1]<1.50)))[0]
own=np.zeros((S,S),bool)
for t in body:
    p=uv[idx[t]]*[S,S]
    x0,y0=np.floor(p.min(0)).astype(int); x1,y1=np.ceil(p.max(0)).astype(int)
    x0,y0=max(x0,0),max(y0,0); x1,y1=min(x1,S-1),min(y1,S-1)
    if x1<x0 or y1<y0 or (x1-x0)*(y1-y0)>40000: continue
    gx,gy=np.meshgrid(np.arange(x0,x1+1)+.5,np.arange(y0,y1+1)+.5)
    (ax,ay),(bx,by),(cx,cy)=p
    d=(by-cy)*(ax-cx)+(cx-bx)*(ay-cy)
    if abs(d)<1e-12: continue
    l1=((by-cy)*(gx-cx)+(cx-bx)*(gy-cy))/d; l2=((cy-ay)*(gx-cx)+(ax-cx)*(gy-cy))/d; l3=1-l1-l2
    own[y0:y1+1,x0:x1+1]|=(l1>=-0.03)&(l2>=-0.03)&(l3>=-0.03)
ch=own&(np.abs(cur.astype(int)-pre.astype(int)).max(2)>6)
print('body tris',len(body),'texels reverted',ch.sum())
out=np.where(own[...,None],pre,cur)
Image.fromarray(out).save(sys.argv[2],quality=92,method=6)
