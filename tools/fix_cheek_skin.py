import numpy as np, sys
from PIL import Image
S=2048
src=sys.argv[1]; dst=sys.argv[2]; ZMIN=float(sys.argv[3]); XMAX=float(sys.argv[4])
cur=np.array(Image.open(src).convert('RGB')).astype(np.float32)/255
org=np.array(Image.open('orig/tex.jpeg').convert('RGB').resize((S,S))).astype(np.float32)/255
uv=np.fromfile('0_uv.bin',np.float32).reshape(-1,2); pos=np.fromfile('0_pos.bin',np.float32).reshape(-1,3)
idx=np.fromfile('0_idx.bin',np.uint32).reshape(-1,3)
V=pos[idx]; c=V.mean(1)
reg=np.where((np.abs(c[:,0])>0.03)&(np.abs(c[:,0])<0.10)&(c[:,1]>1.46)&(c[:,1]<1.64)&(c[:,2]>-0.05))[0]
occ=np.where((np.abs(c[:,0])<0.13)&(c[:,1]>1.40)&(c[:,1]<1.70)&(c[:,2]>-0.10))[0]
A=V[occ,0];E1=V[occ,1]-A;E2=V[occ,2]-A
cand=reg[(np.abs(c[reg,0])>0.04)&(np.abs(c[reg,0])<XMAX)&(c[reg,2]>ZMIN)]
inner=[]
for t in cand:
    o=np.array([0.0,c[t,1],0.0]); d=c[t]-o; L=np.linalg.norm(d); d/=L
    P=np.cross(d,E2); det=(E1*P).sum(1); ok=np.abs(det)>1e-12
    inv=np.where(ok,1/np.where(ok,det,1),0); Tv=o-A
    u=(Tv*P).sum(1)*inv; Q=np.cross(Tv,E1); v=(d*Q).sum(1)*inv; tt=(E2*Q).sum(1)*inv
    hit=ok&(u>=0)&(v>=0)&(u+v<=1)&(tt>L-0.008)&(tt<L-0.0015)
    if not hit.any(): inner.append(t)
print('candidates',len(cand),'innermost skin-surface tris',len(inner))
def tm(t):
    p=uv[idx[t]]*[S,S]
    x0,y0=np.floor(p.min(0)).astype(int); x1,y1=np.ceil(p.max(0)).astype(int)
    x0,y0=max(x0,0),max(y0,0); x1,y1=min(x1,S-1),min(y1,S-1)
    if x1<x0 or y1<y0 or (x1-x0)*(y1-y0)>40000: return None
    gx,gy=np.meshgrid(np.arange(x0,x1+1)+.5,np.arange(y0,y1+1)+.5)
    (ax,ay),(bx,by),(cx,cy)=p
    d=(by-cy)*(ax-cx)+(cx-bx)*(ay-cy)
    if abs(d)<1e-12: return None
    l1=((by-cy)*(gx-cx)+(cx-bx)*(gy-cy))/d; l2=((cy-ay)*(gx-cx)+(ax-cx)*(gy-cy))/d; l3=1-l1-l2
    ins=(l1>=-0.05)&(l2>=-0.05)&(l3>=-0.05)
    return ((slice(y0,y1+1),slice(x0,x1+1)),ins) if ins.sum() else None
oskin=((org[:,:,0]-org[:,:,2])>0.03)&((org@[.3,.59,.11])>0.45)
cpur=((cur[:,:,2]-cur[:,:,1])>0.04)
area=np.zeros((S,S),bool); n=0
for t in inner:
    r=tm(t)
    if not r: continue
    sl,ins=r
    if (oskin[sl]&ins).sum()/ins.sum()<0.5: continue   # skin in the original only
    area[sl]|=ins; n+=1
rest=area&cpur&oskin
print('skin tris',n,'texels restored',rest.sum())
out=np.where(rest[...,None],org,cur)
Image.fromarray((out*255+.5).clip(0,255).astype(np.uint8)).save(dst,quality=92,method=6)
np.save('inner.npy',np.array(inner))
