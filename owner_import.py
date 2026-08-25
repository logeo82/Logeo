import json
import re
from html.parser import HTMLParser
from urllib.request import Request, urlopen
from urllib.parse import urlparse
from datetime import datetime
from flask import request, jsonify
import app as logeo

class _Parser(HTMLParser):
    def __init__(self):
        super().__init__(); self.meta={}; self.jsonld=[]; self._json=False; self._buf=[]; self._title=[]
    def handle_starttag(self, tag, attrs):
        a=dict(attrs)
        if tag=='meta':
            key=(a.get('property') or a.get('name') or a.get('itemprop') or '').lower()
            if key:self.meta[key]=a.get('content','')
        elif tag=='title': self._title=[]
        elif tag=='script' and a.get('type','').lower().split(';')[0].strip()=='application/ld+json': self._json=True; self._buf=[]
    def handle_endtag(self, tag):
        if tag=='title' and self._title:self.meta['title']=''.join(self._title).strip(); self._title=[]
        elif tag=='script' and self._json:
            raw=''.join(self._buf).strip()
            if raw:
                try:self.jsonld.append(json.loads(raw))
                except Exception:pass
            self._json=False; self._buf=[]
    def handle_data(self,data):
        if self._json:self._buf.append(data)
        elif self._title is not None and len(self._title)>=0:self._title.append(data)

def _walk(x):
    if isinstance(x,dict):
        yield x
        for v in x.values():yield from _walk(v)
    elif isinstance(x,list):
        for v in x:yield from _walk(v)

def _number(v):
    if v is None:return None
    if isinstance(v,(int,float)):return float(v)
    s=str(v).replace('\u00a0',' ')
    m=re.search(r'([0-9][0-9 .]*)(?:[,.]([0-9]+))?',s)
    if not m:return None
    a=m.group(1).replace(' ','').replace('.',''); dec=m.group(2)
    try:return float(a+(('.'+dec) if dec else ''))
    except:return None

def _first(*vals):return next((v for v in vals if v not in (None,'',[])),None)
def _canonical_url(url):
    p=urlparse(url);return f'{p.scheme.lower()}://{p.netloc.lower()}{p.path.rstrip("/")}'

def _photos_from_parser(p,text):
    found=[];seen=set()
    def add(u):
        if not isinstance(u,str):return
        u=u.strip().replace('\\/','/')
        if u.startswith('//'):u='https:'+u
        if not u.startswith(('http://','https://')):return
        if any(x in u.lower() for x in ('logo','icon','favicon','sprite')):return
        if u not in seen:seen.add(u);found.append(u)
    for k in ('og:image','twitter:image','image'):
        add(p.meta.get(k))
    for root in p.jsonld:
        for o in _walk(root):
            if not isinstance(o,dict):continue
            for k in ('image','images','photo','photos','pictures','media'):
                v=o.get(k)
                for item in (v if isinstance(v,list) else [v]):
                    if isinstance(item,dict):
                        for key in ('url','contentUrl','src','imageUrl','photoUrl'):add(item.get(key))
                    else:add(item)
    for m in re.finditer(r'https?:\\?/\\?/[^\"\'<>\\s]+?\\.(?:jpe?g|png|webp)(?:\\?[^\"\'<>\\s]*)?',text,re.I):add(m.group(0))
    return found[:30]

def _text_number(text, patterns):
    for pat in patterns:
        m=re.search(pat,text,re.I)
        if m:
            n=_number(m.group(1))
            if n is not None:return n
    return None

def _extract_from_html(url,raw):
    text=raw.decode('utf-8','ignore');p=_Parser();p.feed(text);objs=[o for j in p.jsonld for o in _walk(j)]
    obj=next((o for o in objs if isinstance(o,dict) and ('price' in o or 'offers' in o or o.get('@type') in ('Apartment','Residence','Offer'))),{})
    offers=obj.get('offers') if isinstance(obj.get('offers'),dict) else {}
    title=_first(obj.get('name'),p.meta.get('og:title'),p.meta.get('twitter:title'),p.meta.get('title'))
    desc=_first(obj.get('description'),p.meta.get('description'),p.meta.get('og:description'),'')
    price=_number(_first(offers.get('price'),obj.get('price'),p.meta.get('product:price:amount'),p.meta.get('price')))
    surface=_number(_first(obj.get('surface'),obj.get('area'),p.meta.get('surface')))
    fs=obj.get('floorSize')
    if surface is None and isinstance(fs,dict):surface=_number(fs.get('value'))
    visible=re.sub(r'<[^>]+>',' ',text);visible=re.sub(r'\s+',' ',visible)
    if price is None:price=_text_number(visible,[r'(?:loyer|prix|montant)[^0-9]{0,80}([0-9][0-9 .]{2,})\s*€',r'([0-9][0-9 .]{2,})\s*€\s*(?:/\s*mois|par mois)'])
    if surface is None:surface=_text_number(visible,[r'(?:surface|superficie)[^0-9]{0,40}([0-9]+(?:[,.][0-9]+)?)\s*m²',r'([0-9]+(?:[,.][0-9]+)?)\s*m²'])
    city=_first((obj.get('address') or {}).get('addressLocality') if isinstance(obj.get('address'),dict) else None,p.meta.get('addresslocality'))
    if not city:
        m=re.search(r'\b(montauban|toulouse|albi|caussade|castelsarrasin|moissac)\b',visible,re.I);city=m.group(1).title() if m else 'Montauban'
    low=(title or '')+' '+desc+' '+visible[:150000]
    typ='Studio' if re.search(r'\bstudio\b',low,re.I) else ('T2' if re.search(r'\bT2\b',low,re.I) else ('T1' if re.search(r'\bT1\b',low,re.I) else 'Appartement'))
    furnished=1 if re.search(r'\bmeubl[ée]|furnished\b',low,re.I) else 0
    if price is None:raise ValueError('Le prix n’est pas exposé dans les données publiques accessibles. LOGEO ne peut pas l’inventer.')
    return {'title':str(title or f'{typ} à louer à {city}').strip(),'city':str(city).strip(),'price':price,'surface':surface or 0,'type':typ,'furnished':furnished,'description':str(desc).strip()[:5000],'source':urlparse(url).netloc.lower().replace('www.',''),'source_url':_canonical_url(url),'photos':json.dumps(_photos_from_parser(p,text),ensure_ascii=False)}

def parse_url(url):
    p=urlparse(url)
    if p.scheme not in ('http','https'):raise ValueError('URL invalide')
    req=Request(url,headers={'User-Agent':'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/151 Safari/537.36','Accept-Language':'fr-FR,fr;q=0.9,en;q=0.8','Accept':'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'})
    try:
        with urlopen(req,timeout=20) as r:raw=r.read(8000000)
    except Exception as e:raise ValueError(f'Impossible d’accéder au site ({type(e).__name__}). Le portail peut bloquer les accès automatisés.')
    return _extract_from_html(url,raw)

@logeo.app.post('/api/import-url')
def import_url():
    try:
        u=logeo.user()
        if not u:return jsonify(error='Connexion requise'),401
        if u['role']!='owner':return jsonify(error='Import réservé aux propriétaires / agences'),403
        payload=request.get_json(silent=True) or {};url=str(payload.get('url') or '').strip()
        if not url:return jsonify(error='Colle le lien de l’annonce'),400
        data=parse_url(url);c=logeo.db()
        try:
            try:c.execute('ALTER TABLE listings ADD COLUMN photos TEXT')
            except Exception:pass
            canonical=data['source_url'];existing=None
            for row in c.execute('SELECT * FROM listings WHERE source_url IS NOT NULL').fetchall():
                if _canonical_url(str(row['source_url']))==canonical:existing=row;break
            if existing:return jsonify(ok=True,duplicate=True,listing=dict(existing))
            cur=c.execute('INSERT INTO listings(title,city,price,surface,type,distance_km,furnished,available_date,source,source_url,description,owner_id,created_at,photos) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)',(data['title'],data['city'],data['price'],data['surface'],data['type'],0,data['furnished'],None,data['source'],canonical,data['description'],u['id'],datetime.utcnow().isoformat(),data.get('photos','[]')))
            c.commit();row=c.execute('SELECT * FROM listings WHERE id=?',(cur.lastrowid,)).fetchone();return jsonify(ok=True,duplicate=False,listing=dict(row))
        finally:c.close()
    except ValueError as e:return jsonify(error=str(e)),422
    except Exception as e:return jsonify(error=f'Erreur LOGEO pendant l’import : {type(e).__name__}'),500

@logeo.app.after_request
def ensure_owner_import_box(response):
    """Always expose the importer in the owner page, independently of the exact HTML wording."""
    try:
        if response.content_type and response.content_type.startswith('text/html'):
            page=response.get_data(as_text=True)
            if 'id="ownerApp"' in page and 'id="ownerImportBox"' not in page:
                block='''<div id="ownerImportBox" class="card" style="border:2px solid #111827;margin-bottom:16px"><h3>🔗 Importer une annonce</h3><p class="muted">Colle le lien public d’une annonce Bien’ici ou d’un autre portail immobilier. LOGEO va essayer de récupérer automatiquement le prix, la surface, les photos et les informations disponibles.</p><div style="display:flex;gap:8px;flex-wrap:wrap"><input id="ownerImportUrl" type="url" placeholder="https://www.bienici.com/annonce/..." style="flex:1;min-width:220px"><button id="ownerImportBtn" type="button">📥 Importer l’annonce</button></div><p id="ownerImportMsg" style="margin-bottom:0"></p></div><script>(function(){function init(){var b=document.getElementById('ownerImportBtn');if(!b||b.dataset.ready)return;b.dataset.ready='1';b.onclick=async function(){var input=document.getElementById('ownerImportUrl'),msg=document.getElementById('ownerImportMsg'),url=input.value.trim();if(!url){msg.textContent='❌ Colle d’abord le lien de l’annonce.';msg.className='err';return}b.disabled=true;b.textContent='⏳ Import en cours…';msg.textContent='Lecture des données publiques de l’annonce…';msg.className='muted';try{var r=await fetch('/api/import-url',{method:'POST',headers:{'Content-Type':'application/json','Accept':'application/json'},body:JSON.stringify({url:url})});var raw=await r.text(),x;try{x=JSON.parse(raw)}catch(e){throw Error('Le serveur LOGEO n’a pas renvoyé de JSON (HTTP '+r.status+').')};if(!r.ok)throw Error(x.error||'Import impossible');msg.textContent=x.duplicate?'⚠️ Cette annonce est déjà importée.':'✅ Annonce importée avec succès !';msg.className='ok';input.value='';if(typeof loadOwner==='function')loadOwner()}catch(e){msg.textContent='❌ '+e.message;msg.className='err'}finally{b.disabled=false;b.textContent='📥 Importer l’annonce'}}}if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init);else setTimeout(init,0)})();</script>'''
                marker='<section id="ownerApp"'
                pos=page.find(marker)
                if pos>=0:
                    insert=page.find('>',pos)
                    if insert>=0:page=page[:insert+1]+block+page[insert+1:]
                response.set_data(page)
    except Exception:
        pass
    return response
