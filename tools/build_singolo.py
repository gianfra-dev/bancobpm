#!/usr/bin/env python3
"""Crea un unico file HTML (pagina iniziale + 20 regioni) a partire dalle pagine gia' generate da build.py.
Ogni pagina regionale e' compressa (gzip) e decompressa nel browser solo quando serve (DecompressionStream).
Logo (ed eventuali font) sono incorporati nel file. Le librerie della mappa (Leaflet) e le tessere OpenStreetMap restano online.
Uso: python3 build_singolo.py [file_output]      (default: ../filiali-bpm-ca.html)
     Per impostazione predefinita le pagine vengono rigenerate in una cartella temporanea con confini semplificati (~110 m, EPS=0.001)
     e il file risulta piu' leggero. DATI=<cartella_dati> indica i dati scaricati da fetch.sh; SENZA_SEMPLIFICARE=1 usa le pagine gia' generate."""
import os,re,sys,glob,json,base64,zlib,subprocess,tempfile
HERE=os.path.dirname(os.path.abspath(__file__));ROOT=os.path.abspath(os.path.join(HERE,'..'))
OUT=sys.argv[1] if len(sys.argv)>1 else f'{ROOT}/filiali-bpm-ca.html'
SRC=ROOT   # cartella con le pagine da inglobare
if os.environ.get('DATI') and not os.environ.get('SENZA_SEMPLIFICARE'):
    SRC=tempfile.mkdtemp();subprocess.run([sys.executable,f'{HERE}/build.py',os.environ['DATI'],SRC],check=True,env={**os.environ,'EPS':os.environ.get('EPS','0.001')},stdout=subprocess.DEVNULL)
b64=lambda p,m:f'data:{m};base64,'+base64.b64encode(open(p,'rb').read()).decode()
logo=b64(f'{ROOT}/assets/fisac-logo.png','image/png')
FD=f'{ROOT}/assets/fonts'   # font web opzionali: se la cartella non esiste si usano i font di sistema
FONTS={os.path.basename(f)[:-6]:b64(f,'font/woff2') for f in sorted(glob.glob(f'{FD}/*.woff2'))}
gz=lambda s:base64.b64encode((lambda c:c.compress(s.encode('utf-8'))+c.flush())(zlib.compressobj(9,zlib.DEFLATED,31))).decode()
def strip_assets(h,pre):
    h=re.sub(r'<link rel="preload"[^>]*assets/fonts[^>]*>\s*','',h)
    h=h.replace(f'<link rel="icon" href="{pre}assets/fisac-logo.png">','')
    for n in FONTS:h=h.replace(f'url({pre}assets/fonts/{n}.woff2)',f'url(@@F:{n}@@)')
    return h.replace(f'{pre}assets/fisac-logo.png','@@LOGO@@')
land=strip_assets(open(f'{SRC}/index.html',encoding='utf-8').read(),'')
for n,u in FONTS.items():land=land.replace(f'@@F:{n}@@',u)
land=land.replace('@@LOGO@@',logo)
blocks=[];slugs=[];raw=0
for p in sorted(glob.glob(f'{SRC}/*/index.html')):
    slug=os.path.basename(os.path.dirname(p))
    h=open(p,encoding='utf-8').read()
    if '<a class="back" href="../"' not in h:continue
    h=strip_assets(h,'../')
    h=h.replace('<a class="back" href="../"','<a class="back" href="#" onclick="parent.postMessage(\'home\',\'*\');return false"')
    assert 'onclick="parent.postMessage' in h and '../assets' not in h,slug
    raw+=len(h);blocks.append(f'<script type="text/plain" id="r-{slug}">{gz(h)}</script>');slugs.append(slug)
fonts_js=json.dumps(FONTS)
js='''<script>
(function(){
var S=%s,F=%s,fr=null,tok=0;
function gunz(b){var bin=atob(b),u=new Uint8Array(bin.length);for(var i=0;i<bin.length;i++)u[i]=bin.charCodeAt(i);
  return new Response(new Blob([u]).stream().pipeThrough(new DecompressionStream('gzip'))).text()}
function open(s,push){var el=document.getElementById('r-'+s);if(!el)return;
  if(typeof DecompressionStream==='undefined'){alert('Questo browser e\\' troppo vecchio per aprire la mappa: aggiornalo.');return}
  var t=++tok;
  gunz(el.textContent.trim()).then(function(h){if(t!==tok)return;if(fr)fr.remove();
    h=h.split('@@LOGO@@').join(document.querySelector('nav img').src);
    for(var n in F)h=h.split('@@F:'+n+'@@').join(F[n]);
    fr=document.createElement('iframe');fr.srcdoc=h;
    fr.style.cssText='position:fixed;inset:0;width:100%%;height:100%%;border:0;background:#fff;z-index:9999';
    document.body.appendChild(fr);document.documentElement.style.overflow='hidden';if(push)location.hash=s})}
function home(){tok++;if(fr){fr.remove();fr=null}document.documentElement.style.overflow=''}
document.addEventListener('click',function(e){var a=e.target.closest&&e.target.closest('a[href]');if(!a)return;
  var m=(a.getAttribute('href')||'').match(/^([a-z-]+)\\/$/);if(m&&S.indexOf(m[1])>=0){e.preventDefault();open(m[1],true)}},true);
window.addEventListener('message',function(e){if(e.data==='home'){home();history.replaceState(null,'',location.pathname+location.search)}});
window.addEventListener('hashchange',function(){var s=location.hash.slice(1);s&&S.indexOf(s)>=0?open(s,false):home()});
var s=location.hash.slice(1);if(s&&S.indexOf(s)>=0)open(s,false);
})();
</script>'''%(json.dumps(slugs),fonts_js)
assert '</body>' in land and 'assets/' not in land.replace('assets/fisac','X'),'riferimenti a assets rimasti'
land=land.replace('</body>',''.join(blocks)+js+'</body>')
open(OUT,'w',encoding='utf-8').write(land)
print(len(slugs),'regioni ->',OUT,round(os.path.getsize(OUT)/1e6,2),'MB (pagine non compresse:',round(raw/1e6,1),'MB)')
