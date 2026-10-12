import numpy as np, sys
from PIL import Image
from scipy import ndimage, sparse
S=2048; THR=0.5; RINGS=int(sys.argv[1]) if len(sys.argv)>1 else 4
uv=np.fromfile('0_uv.bin',np.float32).reshape(-1,2); pos=np.fromfile('0_pos.bin',np.float32).reshape(-1,3)
hair=np.fromfile('0_hair.bin',np.float32); idx=np.fromfile('0_idx.bin',np.uint32).reshape(-1,3)
rgb=np.array(Image.open('chinfixed2.webp').convert('RGB')).astype(np.float32)/255
lum=rgb@[.3,.59,.11]
good=((rgb[:,:,2]-rgb[:,:,1])>0.08)&(lum<0.6)
skin=(rgb[:,:,0]-rgb[:,:,2])>0.06
neu=((rgb.max(2)-rgb.min(2))<0.07)&(lum>0.45)
y=pos[:,1]; H=y.max()
cand=np.where((y[idx]>1.42).all(1))[0]
info={}
for ti in cand:
    t=idx[ti]; p=uv[t]*[S,S]
    x0,y0=np.floor(p.min(0)).astype(int); x1,y1=np.ceil(p.max(0)).astype(int)
    x0,y0=max(x0,0),max(y0,0); x1,y1=min(x1,S-1),min(y1,S-1)
    if x1<x0 or y1<y0 or (x1-x0)*(y1-y0)>40000: continue
    gx,gy=np.meshgrid(np.arange(x0,x1+1)+.5,np.arange(y0,y1+1)+.5)
    (ax,ay),(bx,by),(cx,cy)=p
    d=(by-cy)*(ax-cx)+(cx-bx)*(ay-cy)
    if abs(d)<1e-12: continue
    l1=((by-cy)*(gx-cx)+(cx-bx)*(gy-cy))/d; l2=((cy-ay)*(gx-cx)+(ax-cx)*(gy-cy))/d; l3=1-l1-l2
    ins=(l1>=-0.03)&(l2>=-0.03)&(l3>=-0.03)
    n=ins.sum()
    if n==0: continue
    sl=(slice(y0,y1+1),slice(x0,x1+1))
    info[ti]=(sl,ins,(good[sl]&ins).sum()/n,max((skin[sl]&ins).sum()/n,(neu[sl]&ins).sum()/n))
JAW=set(np.load('jaw.npy').tolist())
high=lambda ti: pos[idx[ti],1].min()>1.42 and ti not in JAW
hairT=set(ti for ti,(sl,ins,fg,fs) in info.items() if (hair[idx[ti]].min()>0.5 and ti not in JAW) or (fg>=THR and high(ti)))
base=len(hairT)
# grow along shared vertex indices (= same UV island), never into skin-coloured triangles
v2t={}
for ti in info:
    for v in idx[ti]: v2t.setdefault(int(v),[]).append(ti)
front=set(hairT)
for r in range(RINGS):
    nxt=set()
    for ti in front:
        for v in idx[ti]:
            for tj in v2t[int(v)]:
                if tj not in hairT and info[tj][3]<0.25 and high(tj): nxt.add(tj)
    hairT|=nxt; front=nxt
print('base tris',base,'after growth',len(hairT))
import json
from collections import deque
key=np.round(pos/1e-5).astype(np.int64); _,wid=np.unique(key,axis=0,return_inverse=True); wid=wid.ravel()
w2t={}
for ti in info:
    for v in idx[ti]: w2t.setdefault(int(wid[v]),[]).append(ti)
neu_=((rgb.max(2)-rgb.min(2))<0.07)&(lum>0.45)
neuT={t for t,(sl,ins,fg,fs) in info.items() if (neu_[sl]&ins).sum()/ins.sum()>=0.6}
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
# white strand tips: small white clusters (not the mask) hanging off hair triangles
tips=0
for t0 in neuT-prot:
    pass
seen=set()
for t0 in neuT-prot:
    if t0 in seen: continue
    comp=[]; q=deque([t0]); seen.add(t0)
    while q:
        t=q.popleft(); comp.append(t)
        for v in idx[t]:
            for tj in w2t[int(wid[v])]:
                if tj in neuT and tj not in prot and tj not in seen: seen.add(tj); q.append(tj)
    nb=set()
    for t in comp:
        for v in idx[t]:
            for tj in w2t[int(wid[v])]:
                if tj not in neuT: nb.add(tj)
    if nb and all(high(t) for t in comp) and sum(t in hairT for t in nb)/len(nb)>=0.6:
        hairT.update(comp); tips+=len(comp)
print('tip triangles added',tips)
area=np.zeros((S,S),bool)
for ti in hairT:
    sl,ins,_,_=info[ti]; area[sl]|=ins
ml=np.median(lum[area&good]); print('median',ml)
bad=area&(~good|(lum>ml*1.4))
print('repaint texels',bad.sum())
src=area&good
_,(iy,ix)=ndimage.distance_transform_edt(~src,return_indices=True)
out=np.where(bad[...,None],rgb[iy,ix],rgb)
bl=ndimage.uniform_filter(out,size=(3,3,1))
out=np.where(bad[...,None],bl*0.5+out*0.5,out)
Image.fromarray((out*255+.5).clip(0,255).astype(np.uint8)).save('fixed.png')
