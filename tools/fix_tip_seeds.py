import numpy as np, json
from PIL import Image
from scipy import ndimage
from collections import deque
S=2048; R=0.012; YMAX=1.548
rgb=np.array(Image.open('final.webp').convert('RGB')).astype(np.float32)/255
uv=np.fromfile('0_uv.bin',np.float32).reshape(-1,2); pos=np.fromfile('0_pos.bin',np.float32).reshape(-1,3)
idx=np.fromfile('0_idx.bin',np.uint32).reshape(-1,3)
lum=rgb@[.3,.59,.11]
good=((rgb[:,:,2]-rgb[:,:,1])>0.08)&(lum<0.6)
neu=((rgb.max(2)-rgb.min(2))<0.07)&(lum>0.45)
c=pos[idx].mean(1)
near=np.where((c[:,1]>1.40)&(c[:,1]<1.62)&(np.abs(c[:,0])<0.12))[0]
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
for t in near:
    r=tm(t)
    if r: info[t]=r
gfrac={t:(good[sl]&ins).sum()/ins.sum() for t,(sl,ins) in info.items()}
nfrac={t:(neu[sl]&ins).sum()/ins.sum() for t,(sl,ins) in info.items()}
key=np.round(pos/1e-5).astype(np.int64); _,wid=np.unique(key,axis=0,return_inverse=True); wid=wid.ravel()
w2t={}
for t in info:
    for v in idx[t]: w2t.setdefault(int(wid[v]),[]).append(t)
# mask = big welded white cluster: never touched
neuT={t for t in info if nfrac[t]>=0.6}
seen=set(); prot=set()
for t0 in neuT:
    if t0 in seen: continue
    comp=[]; q=deque([t0]); seen.add(t0)
    while q:
        t=q.popleft(); comp.append(t)
        for v in idx[t]:
            for tj in w2t[int(wid[v])]:
                if tj in neuT and tj not in seen: seen.add(tj); q.append(tj)
    if len(comp)>150: prot.update(comp)
picks=[p for p in json.load(open('tippicks1.json')) if p[2]<YMAX]
seeds=[(int(p[0]),np.array(p[1:4])) for p in picks]
# mirror every pick to the other side of the face
cand=np.array(list(info.keys())); cc=c[cand]
for _,pt in list(seeds):
    m=pt*[-1,1,1]; j=cand[np.argmin(((cc-m)**2).sum(1))]; seeds.append((int(j),m))
fix=set()
for t0,pt in seeds:
    if t0 not in info or t0 in prot or gfrac[t0]>0.5 or c[t0][1]>YMAX: continue
    q=deque([t0]); fix.add(t0)
    while q:
        t=q.popleft()
        for v in idx[t]:
            for tj in w2t[int(wid[v])]:
                if tj in fix or tj in prot or gfrac[tj]>0.5: continue
                if np.linalg.norm(c[tj]-pt)>R or c[tj][1]>YMAX: continue
                fix.add(tj); q.append(tj)
print('seeds',len(seeds),'tip tris painted',len(fix))
area=np.zeros((S,S),bool)
for t in fix:
    sl,ins=info[t]; area[sl]|=ins
bad=area&~good
src=good&(lum>0.15)
_,(iy,ix)=ndimage.distance_transform_edt(~src,return_indices=True)
out=np.where(bad[...,None],rgb[iy,ix],rgb)
print('texels',bad.sum())
# eye zone: give back the texture from before today's edits (the rig never painted the eyes)
pre=np.array(Image.open('pre/tex.webp').convert('RGB')).astype(np.float32)/255
eyeT=np.where((np.abs(c[:,0])<0.075)&(c[:,1]>YMAX)&(c[:,1]<1.625)&(c[:,2]>0.06))[0]
eye=np.zeros((S,S),bool)
for t in eyeT:
    r=tm(t)
    if r: eye[r[0]]|=r[1]
print('eye-zone texels restored',(eye&(np.abs(out-pre).max(2)>0.03)).sum())
out=np.where(eye[...,None],pre,out)
Image.fromarray((out*255+.5).clip(0,255).astype(np.uint8)).save('final3.webp',quality=92,method=6)
