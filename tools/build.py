#!/usr/bin/env python3
"""Genera le mappe regionali (<regione>/index.html) e la pagina d'accesso (index.html).
Uso: python3 build.py <cartella_dati> [cartella_output]   (dati scaricati con fetch.sh)"""
import re,json,sys,os,unicodedata,collections,datetime,math
DATA=sys.argv[1]; ROOT=os.path.abspath(sys.argv[2] if len(sys.argv)>2 else os.path.join(os.path.dirname(os.path.abspath(__file__)),'..'))
TODAY=datetime.date.today().strftime('%d/%m/%Y')
HERE=os.path.dirname(os.path.abspath(__file__))
dec=json.JSONDecoder()
h=open(f'{DATA}/bt.html').read();seen={}
for m in re.finditer(r'\{"Lat"',h):
    try:o,_=dec.raw_decode(h[m.start():])
    except Exception:continue
    seen[(o.get('ABI'),o.get('CAB'),o.get('CodFiliale'))]=o
c=open(f'{DATA}/ca.html').read()
d=json.loads(re.search(r'__NEXT_DATA__[^>]*>(.*?)</script>',c,re.S).group(1));uf=[]
def find(x):
    if isinstance(x,dict):
        if 'uffici' in x:uf.extend(x['uffici'])
        for v in x.values():find(v)
    elif isinstance(x,list):
        for v in x:find(v)
find(d)
prov=json.load(open(f'{DATA}/prov.geojson'))
def norm(s):
    s=unicodedata.normalize('NFD',s.lower());return re.sub(r'[^a-z]','',''.join(ch for ch in s if not unicodedata.combining(ch)))
def dp(pts,eps):
    if len(pts)<5:return pts
    keep=[False]*len(pts);keep[0]=keep[-1]=True;st=[(0,len(pts)-1)]
    while st:
        a,b=st.pop();ax,ay=pts[a];bx,by=pts[b];dx,dy=bx-ax,by-ay;L=math.hypot(dx,dy) or 1e-12;mx=-1;mi=a
        for i in range(a+1,b):
            dd=abs(dy*(pts[i][0]-ax)-dx*(pts[i][1]-ay))/L
            if dd>mx:mx=dd;mi=i
        if mx>eps:keep[mi]=True;st.append((a,mi));st.append((mi,b))
    return [p for p,k in zip(pts,keep) if k]
EPS=float(os.environ.get('EPS',0.0002));ND=int(os.environ.get('ND',4))   # EPS piu' alto = confini piu' semplici (file piu' leggero)
def simp(coords,eps=None,nd=None):
    eps=EPS if eps is None else eps;nd=ND if nd is None else nd
    out=[]
    for ring in coords:
        m=len(ring)//2;r=dp(ring[:m+1],eps)[:-1]+dp(ring[m:],eps) if len(ring)>=8 else ring;r=[[round(x,nd),round(y,nd)] for x,y in r]
        rr=[];last=None
        for p in r:
            if p!=last:rr.append(p)
            last=p
        if len(rr)>=4:out.append(rr)
    return out
def geom(g):
    polys=[g['coordinates']] if g['type']=='Polygon' else g['coordinates']
    ps=[p for p in (simp(q) for q in polys) if p]
    if not ps:ps=[p for p in (simp(q,0) for q in polys) if p]
    return {'type':'MultiPolygon','coordinates':ps}
def bbox(g):
    xs=[p[0] for q in g['coordinates'] for p in q[0]];ys=[p[1] for q in g['coordinates'] for p in q[0]];return min(xs),min(ys),max(xs),max(ys)
def pip(x,y,ring):
    ins=False;j=len(ring)-1
    for i in range(len(ring)):
        xi,yi=ring[i];xj,yj=ring[j]
        if (yi>y)!=(yj>y) and x<(xj-xi)*(y-yi)/(yj-yi)+xi:ins=not ins
        j=i
    return ins
def inside(x,y,g,bb):
    if not(bb[0]<=x<=bb[2] and bb[1]<=y<=bb[3]):return False
    return any(pip(x,y,p[0]) and not any(pip(x,y,hh) for hh in p[1:]) for p in g['coordinates'])
KEY={'valledaostavalleedaoste':'valledaosta','trentinoaltoadigesudtirol':'trentinoaltoadige'}
regs=json.load(open(f'{DATA}/g/regions.geojson'))['features']
slugof=lambda n:{'valledaostavalleedaoste':'valle-d-aosta','trentinoaltoadigesudtirol':'trentino-alto-adige'}.get(norm(n),re.sub(r'[^a-z]+','-',unicodedata.normalize('NFKD',n.lower()).encode('ascii','ignore').decode()).strip('-'))
SHORT={"Valle d'Aosta/Vallée d'Aoste":"Valle d'Aosta",'Trentino-Alto Adige/Südtirol':'Trentino-Alto Adige'}
def encring(r):   # anello -> [x0,y0,dx,dy,...] in interi (1e-4 gradi): molto piu' compatto; la pagina lo decodifica
    o=[];px=py=0
    for x,y in r:
        X=round(x*1e4);Y=round(y*1e4);o+=[X-px,Y-py];px,py=X,Y
    return o
def enc(fs):return [{**f,'geometry':{'type':'MultiPolygon','coordinates':[[encring(r) for r in p] for p in (f['geometry']['coordinates'] if f['geometry']['type']=='MultiPolygon' else [f['geometry']['coordinates']])]}} for f in fs]
summary=[]
for rf in regs:
    rp=rf['properties'];code=rp['reg_istat_code_num'];rname=SHORT.get(rp['reg_name'],rp['reg_name']);slug=slugof(rp['reg_name'])
    key=KEY.get(norm(rp['reg_name']),norm(rp['reg_name']))
    com=json.load(open(f'{DATA}/g/com{code}.geojson'))
    cf=[];bbs=[]
    for f in com['features']:
        g=geom(f['geometry']);cf.append({'type':'Feature','properties':{'n':f['properties']['name'],'p':f['properties']['prov_acr'],'k':norm(f['properties']['name'])},'geometry':g});bbs.append(bbox(g))
    PROVN={f['properties']['prov_acr']:f['properties']['prov_name'] for f in com['features']}
    pf=[{'type':'Feature','properties':{'p':f['properties']['prov_acr'],'n':f['properties']['prov_name']},'geometry':geom(f['geometry'])} for f in prov['features'] if f['properties']['reg_name']==rp['reg_name']]
    byk={}
    for f in cf:byk.setdefault(f['properties']['k'],[]).append(f)
    def assign(lat,lon,name):
        for f,bb in zip(cf,bbs):
            if inside(lon,lat,f['geometry'],bb):return f['properties']
        cc=byk.get(norm(name));return cc[0]['properties'] if cc else None
    br=[]
    for o in seen.values():
        if not norm(o.get('regione','')).startswith(key):continue
        lat,lon=float(o['Lat']),float(o['Lon']);a=assign(lat,lon,o['Comune']);tp=o.get('tipo')
        br.append({'b':'BPM','nome':o['Denominazione'].title(),'ind':o['Indirizzo'],'cap':o['Cap'],'tel':o.get('Telefono'),'lat':lat,'lon':lon,'com':a['n'] if a else o['Comune'].title(),'prov':a['p'] if a else o['provincia'],'cod':o['CodFiliale'],'tip':{'R':'Filiale','I':'Centro Imprese','C':'Centro Corporate'}.get(tp,tp),'spec':tp!='R','marchio':o['Nome_Banca'].replace('Banco BPM - ',''),'orario':o.get('Orario')})
    for u in uf:
        cm=u.get('comune')
        if not cm or not norm(cm['provincia']['regione']['nome']).startswith(key):continue
        lat,lon=float(u['latitudine']),float(u['longitudine']);a=assign(lat,lon,cm['nome']);t=u['tipologia']['nome']
        br.append({'b':'CA','nome':u['nome'].title(),'ind':u['indirizzo'],'cap':'','tel':u.get('telefono'),'lat':lat,'lon':lon,'com':a['n'] if a else cm['nome'],'prov':a['p'] if a else cm['provincia']['sigla'],'cod':u['codice'],'tip':t,'spec':t in ("Mercato d'Impresa",'Mercato Private','Area Large Corporate','Consulenti Finanziari'),'marchio':'Crédit Agricole Italia','orario':u.get('orarioAperturaRegolare')})
    names={f['properties']['n'] for f in cf}
    bad=[(b['b'],b['nome'],b['com']) for b in br if b['com'] not in names]
    cnt=collections.Counter((b['com'],b['b']) for b in br)
    both=len([k for k in cnt if k[1]=='BPM' and (k[0],'CA') in cnt])
    nb=sum(b['b']=='BPM' for b in br);nc=len(br)-nb
    # coppie entro 500 m
    P=0
    for a in br:
        if a['b']!='BPM':continue
        for b in br:
            if b['b']=='CA':
                dl=(a['lat']-b['lat'])*111320;dn=(a['lon']-b['lon'])*111320*math.cos(math.radians(a['lat']))
                if dl*dl+dn*dn<=250000:P+=1
    print(f"{rname:22} BPM {nb:4} CA {nc:4} comuni {len(cf):4} sovrapposti {both:3} coppie500 {P:3} fuori-comune {bad}")
    data=json.dumps({'comuni':{'type':'FeatureCollection','features':enc(cf)},'prov':{'type':'FeatureCollection','features':enc(pf)},'br':br},separators=(',',':'),ensure_ascii=False)
    t=open(f'{HERE}/template.html').read()
    for k,v in [('__REG__',rname),('__DATE__',TODAY),('__PROVN__',json.dumps(PROVN,ensure_ascii=False)),('__SLUG__',slug),('__DATA__',data)]:
        t=t.replace(k,v)
    os.makedirs(f'{ROOT}/{slug}',exist_ok=True);open(f'{ROOT}/{slug}/index.html','w').write(t)
    summary.append(dict(slug=slug,name=rname,bpm=nb,ca=nc,comuni=len(cf),both=both,pairs=P,feat=rf))
# ---------- pagina d'accesso ----------
S=60;X0=6.5;Y0=47.2;K=math.cos(math.radians(42))
def proj(p):return [round((p[0]-X0)*K*S,1),round((Y0-p[1])*S,1)]
paths=[]
for s in summary:
    g=s['feat']['geometry'];polys=[g['coordinates']] if g['type']=='Polygon' else g['coordinates'];dstr=''
    for poly in polys:
        if max(p[1] for p in poly[0])<36.4:continue  # Pelagie (Lampedusa, Linosa): nessuna filiale
        ring=[proj(p) for p in poly[0]]
        # scarta isolotti minuscoli
        xs=[p[0] for p in ring];ys=[p[1] for p in ring]
        if (max(xs)-min(xs))*(max(ys)-min(ys))<6:continue
        m=len(ring)//2;r=(dp(ring[:m+1],0.35)[:-1]+dp(ring[m:],0.35)) if len(ring)>=8 else ring
        dstr+='M'+'L'.join(f'{x},{y}' for x,y in r)+'Z'
    paths.append((s,dstr))
W=math.ceil((18.8-X0)*K*S);H=math.ceil((Y0-36.5)*S)
svg=''.join(f'<a href="{s["slug"]}/" class="reg" data-n="{s["name"]}" data-b="{s["bpm"]}" data-c="{s["ca"]}" data-o="{s["both"]}"><title>{s["name"]}</title><path d="{ds}"/></a>' for s,ds in paths)
rows=''.join(f'<a class="tile" href="{s["slug"]}/"><strong>{s["name"]}</strong><dl><div><dd class="g">{s["bpm"]}</dd>BPM</div><div><dd class="b">{s["ca"]}</dd>CA</div><div><dd class="y">{s["both"]}</dd>entrambe</div></dl></a>' for s in sorted(summary,key=lambda s:s['name']))
tb=sum(s['bpm'] for s in summary);tc=sum(s['ca'] for s in summary);to=sum(s['both'] for s in summary)
html=open(f'{HERE}/landing.html').read()
for k,v in [('__SVG__',svg),('__W__',str(W)),('__H__',str(H)),('__ROWS__',rows),('__DATE__',TODAY),('__TB__',str(tb)),('__TC__',str(tc)),('__TO__',str(to))]:html=html.replace(k,v)
open(f'{ROOT}/index.html','w').write(html)
print('TOTALE BPM',tb,'CA',tc,'sovrapposti',to)
