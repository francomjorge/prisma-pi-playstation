#!/usr/bin/env python3
from pathlib import Path
import sys, re, io, zipfile, urllib.parse, urllib.request

OUT = Path(sys.argv[1])
UA = {'User-Agent':'Mozilla/5.0 PRISMA-PS1-build'}
BASE='https://www.models-resource.com'

def get(url):
    req=urllib.request.Request(url,headers=UA)
    with urllib.request.urlopen(req,timeout=30) as r:
        return r.read()

def find_model_page(queries):
    for q in queries:
        url=BASE+'/search/?q='+urllib.parse.quote_plus(q)
        html=get(url).decode('utf-8','ignore')
        links=re.findall(r'href=["\']([^"\']+/model/\d+/?)["\']',html,re.I)
        if not links:
            links=re.findall(r'href=["\']([^"\']*?/model/\d+/?)["\']',html,re.I)
        if links:
            link=links[0]
            return link if link.startswith('http') else BASE+link
    raise RuntimeError('model page not found: '+str(queries))

def download_zip(page):
    html=get(page).decode('utf-8','ignore')
    links=re.findall(r'href=["\']([^"\']*/download/\d+/?)["\']',html,re.I)
    if not links:
        # some pages use a form/action or protocol-relative link
        links=re.findall(r'(/download/\d+/?)',html,re.I)
    if not links:
        raise RuntimeError('download link not found: '+page)
    link=links[0]
    url=link if link.startswith('http') else BASE+link
    return get(url)

def load_obj(zbytes):
    with zipfile.ZipFile(io.BytesIO(zbytes)) as z:
        names=[n for n in z.namelist() if n.lower().endswith('.obj')]
        if not names: raise RuntimeError('OBJ not found')
        text=z.read(names[0]).decode('utf-8','ignore')
    verts=[]; tris=[]
    for line in text.splitlines():
        if line.startswith('v '):
            p=line.split(); verts.append((float(p[1]),float(p[2]),float(p[3])))
        elif line.startswith('f '):
            ids=[]
            for tok in line.split()[1:]:
                i=int(tok.split('/')[0]);
                if i<0: i=len(verts)+i+1
                ids.append(i-1)
            for k in range(1,len(ids)-1): tris.append((ids[0],ids[k],ids[k+1]))
    return verts,tris

def reduce_mesh(v,tris,grid=15,max_tris=300):
    xs=[p[0] for p in v]; ys=[p[1] for p in v]; zs=[p[2] for p in v]
    mn=(min(xs),min(ys),min(zs)); mx=(max(xs),max(ys),max(zs))
    spans=tuple(max(1e-9,mx[i]-mn[i]) for i in range(3))
    cell_sum={}; old_key=[]
    for p in v:
        key=tuple(min(grid-1,int((p[a]-mn[a])/spans[a]*grid)) for a in range(3))
        old_key.append(key)
        if key not in cell_sum: cell_sum[key]=[0.0,0.0,0.0,0]
        c=cell_sum[key]; c[0]+=p[0]; c[1]+=p[1]; c[2]+=p[2]; c[3]+=1
    keys=list(cell_sum); key_idx={k:i for i,k in enumerate(keys)}
    nv=[]
    for k in keys:
        c=cell_sum[k]; nv.append((c[0]/c[3],c[1]/c[3],c[2]/c[3]))
    rem_old=[key_idx[k] for k in old_key]
    nt=[]; seen=set()
    for a,b,c in tris:
        t=(rem_old[a],rem_old[b],rem_old[c])
        if len(set(t))<3: continue
        ck=tuple(sorted(t))
        if ck in seen: continue
        seen.add(ck); nt.append(t)
    if len(nt)>max_tris:
        step=len(nt)/float(max_tris)
        nt=[nt[min(len(nt)-1,int(i*step))] for i in range(max_tris)]
    used=sorted(set(i for t in nt for i in t)); r={x:i for i,x in enumerate(used)}
    nv=[nv[i] for i in used]; nt=[tuple(r[i] for i in t) for t in nt]
    xs=[p[0] for p in nv]; ys=[p[1] for p in nv]; zs=[p[2] for p in nv]
    cen=((min(xs)+max(xs))/2,(min(ys)+max(ys))/2,(min(zs)+max(zs))/2)
    ext=max(max(xs)-min(xs),max(ys)-min(ys),max(zs)-min(zs)); scale=3600.0/ext
    out=[(round((p[0]-cen[0])*scale),round(-(p[1]-cen[1])*scale),round((p[2]-cen[2])*scale)) for p in nv]
    return out,nt

def fetch_character(name,queries):
    page=find_model_page(queries)
    print(name,'page',page)
    v,t=load_obj(download_zip(page))
    v,t=reduce_mesh(v,t)
    print(name,len(v),'verts',len(t),'tris')
    return name,v,t

models=[
    fetch_character('TYRANT',['Resident Evil 2 Tyrant T-103','Tyrant T-103']),
    fetch_character('TREX',['Parasite Eve Tyrannosaurus Rex','Tyrannosaurus Rex Parasite Eve']),
]

p=[]
p.append('// Auto-generated reduced character meshes for 3D PLAY 1.2 selector\n')
p.append('use psx_gte::math::Vec3I16;\n\n')
for name,v,t in models:
    p.append(f'pub const {name}_VERTS: [Vec3I16; {len(v)}] = [\n')
    for x,y,z in v: p.append(f'    Vec3I16::new({x},{y},{z}),\n')
    p.append('];\n\n')
    p.append(f'pub const {name}_FACES: [(u16,u16,u16); {len(t)}] = [\n')
    for a,b,c in t: p.append(f'    ({a},{b},{c}),\n')
    p.append('];\n\n')
OUT.write_text(''.join(p))
print('wrote',OUT)
