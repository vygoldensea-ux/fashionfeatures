import numpy as np, sys
from PIL import Image
S=2048
cur=np.array(Image.open(sys.argv[1]).convert('RGB')).astype(np.float32)/255
org=np.array(Image.open('orig/tex.jpeg').convert('RGB').resize((S,S))).astype(np.float32)/255
uv=np.fromfile('0_uv.bin',np.float32).reshape(-1,2); pos=np.fromfile('0_pos.bin',np.float32).reshape(-1,3)
idx=np.fromfile('0_idx.bin',np.uint32).reshape(-1,3)
c=pos[idx].mean(1)
olum=org@[.3,.59,.11]
opur=((org[:,:,2]-org[:,:,1])>0.05)&(olum<0.6)
diff=np.abs(cur-org).max(2)>0.10
# keep every texel today's hair passes painted (strands, tips): compare before/after those passes
a=np.array(Image.open('chinfixed2.webp').convert('RGB')).astype(np.float32)/255
b=np.array(Image.open('final3.webp').convert('RGB')).astype(np.float32)/255
from scipy import ndimage
hairpass=ndimage.binary_dilation(np.abs(a-b).max(2)>0.03,iterations=2)
diff&=~hairpass
YMAX=float(sys.argv[3]); XMAX=float(sys.argv[4])
zone=np.where((c[:,1]>1.36)&(c[:,1]<YMAX)&(np.abs(c[:,0])<XMAX)&(c[:,2]>-0.04))[0]
tips=set(np.load('tipfix_ids.npy').tolist()) if len(sys.argv)>5 else set()
V=pos[idx]
occ=np.where((np.abs(c[:,0])<0.13)&(c[:,1]>1.30)&(c[:,1]<1.70)&(c[:,2]>-0.10))[0]
A=V[occ,0];E1=V[occ,1]-A;E2=V[occ,2]-A
def innermost(t):
    o=np.array([0.0,c[t,1],0.0]); d=c[t]-o; L=np.linalg.norm(d); d=d/L
    P=np.cross(d,E2); det=(E1*P).sum(1); ok=np.abs(det)>1e-12
    inv=np.where(ok,1/np.where(ok,det,1),0); Tv=o-A
    u=(Tv*P).sum(1)*inv; Q=np.cross(Tv,E1); v=(d*Q).sum(1)*inv; tt=(E2*Q).sum(1)*inv
    return not (ok&(u>=0)&(v>=0)&(u+v<=1)&(tt>L-0.008)&(tt<L-0.0015)).any()
restore=np.zeros((S,S),bool); n=0; ni=0
for t in zone:
    if t in tips: continue
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
    if (opur[sl]&ins).sum()/ins.sum()>=0.15: continue   # a real hair strand in the original
    inn=innermost(t); ni+=inn
    dd=(np.abs(cur-org).max(2)[sl]>0.10) if inn else diff[sl]
    restore[sl]|=ins&dd&~opur[sl]; n+=1
print('innermost',ni,'tris',n,'restored texels',restore.sum())
out=np.where(restore[...,None],org,cur)
Image.fromarray((out*255+.5).clip(0,255).astype(np.uint8)).save(sys.argv[2],quality=92,method=6)
