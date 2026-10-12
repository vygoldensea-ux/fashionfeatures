import numpy as np, sys
from PIL import Image
from collections import deque
S=2048
cur=np.array(Image.open(sys.argv[1]).convert('RGB')).astype(np.float32)/255
org=np.array(Image.open('orig/tex.jpeg').convert('RGB').resize((S,S))).astype(np.float32)/255
uv=np.fromfile('0_uv.bin',np.float32).reshape(-1,2); pos=np.fromfile('0_pos.bin',np.float32).reshape(-1,3)
idx=np.fromfile('0_idx.bin',np.uint32).reshape(-1,3)
c=pos[idx].mean(1)
olum=org@[.3,.59,.11]; osat=org.max(2)-org.min(2)
oneu=(osat<0.06)&(olum>0.15)
head=np.where((c[:,1]>1.38)&(c[:,1]<1.62)&(np.abs(c[:,0])<0.12))[0]
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
info={}
for t in head:
    r=tm(t)
    if r: info[t]=r
neuT={t for t,(sl,ins) in info.items() if (oneu[sl]&ins).sum()/ins.sum()>=0.6}
key=np.round(pos/1e-5).astype(np.int64); _,wid=np.unique(key,axis=0,return_inverse=True); wid=wid.ravel()
w2t={}
for t in info:
    for v in idx[t]: w2t.setdefault(int(wid[v]),[]).append(t)
seen=set(); mask=set(); sizes=[]
for t0 in neuT:
    if t0 in seen: continue
    comp=[]; q=deque([t0]); seen.add(t0)
    while q:
        t=q.popleft(); comp.append(t)
        for v in idx[t]:
            for tj in w2t[int(wid[v])]:
                if tj in neuT and tj not in seen: seen.add(tj); q.append(tj)
    sizes.append(len(comp))
    if len(comp)>300: mask.update(comp)
print('original white clusters',sorted(sizes)[-5:],'mask tris',len(mask))
area=np.zeros((S,S),bool)
for t in mask:
    sl,ins=info[t]; area[sl]|=ins
rest=area&oneu&(np.abs(cur-org).max(2)>0.06)
print('mask texels restored',rest.sum())
out=np.where(rest[...,None],org,cur)
Image.fromarray((out*255+.5).clip(0,255).astype(np.uint8)).save(sys.argv[2],quality=92,method=6)
