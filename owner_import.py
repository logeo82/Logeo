import json
import re
from html.parser import HTMLParser
from urllib.request import Request, urlopen
from urllib.parse import urlparse, urlunparse
from datetime import datetime
from flask import request, jsonify
import app as logeo

class _Parser(HTMLParser):
    def __init__(self):
        super().__init__(); self.meta={}; self.jsonld=[]; self._json=False; self._buf=[]
    def handle_starttag(self, tag, attrs):
        a=dict(attrs)
        if tag=='meta':
            key=(a.get('property') or a.get('name') or a.get('itemprop') or '').lower()
            if key: self.meta[key]=a.get('content','')
        elif tag=='title': self._buf=[]
        elif tag=='script' and a.get('type','').lower()=='application/ld+json': self._json=True; self._buf=[]
    def handle_endtag(self, tag):
        if tag=='title' and self._buf:
            self.meta['title']=''.join(self._buf).strip(); self._buf=[]
        elif tag=='script' and self._json:
            raw=''.join(self._buf).strip()
            if raw:
                try:self.jsonld.append(json.loads(raw))
                except Exception:pass
            self._json=False; self._buf=[]
    def handle_data(self, data):
        if self._json or 'title' not in self.meta:self._buf.append(data)

def _walk(x):
    if isinstance(x,dict):
        yield x
        for v in x.values(): yield from _walk(v)
    elif isinstance(x,list):
        for v in x: yield from _walk(v)

def _number(v):
    if v is None:return None
    s=str(v).replace('\u202f',' ').replace('\xa0',' ').strip()
    m=re.search(r'([0-9][0-9 .]*)(?:[,\.]([0-9]{1,2}))?',s)
    if not m:return None
    a=m.group(1).replace(' ','').replace('.','')
    try:return float(a+(('.'+m.group(2)) if m.group(2) else ''))
    except:return None

def _find_price(text, meta, objs):
    # Bien'ici and similar sites often expose the value in JSON/JS rather than JSON-LD.
    keys=('product:price:amount','og:price:amount','price','priceamount','itemprop:price','offer:price','og:price')
    for k in keys:
        if meta.get(k):
            n=_number(meta[k])
            if n is not None and 50 <= n <= 10000000:return n
    # Search every JSON-LD object, not only the first matching object.
    for o in objs:
        if not isinstance(o,dict): continue
        for key in ('price','lowPrice','highPrice'):
            n=_number(o.get(key))
            if n is not None and 50 <= n <= 10000000:return n
        offers=o.get('offers')
        if isinstance(offers,dict):
            for key in ('price','lowPrice','highPrice'):
                n=_number(offers.get(key))
                if n is not None and 50 <= n <= 10000000:return n
    # Public HTML/JS fallback. Prefer explicit rental/price labels and common JSON keys.
    patterns=[
        r'(?i)(?:prix|loyer|montant|rent|price)\s*["\'=:> ]+\s*([0-9][0-9 .\u00a0\u202f]*)(?:[,\.]\d{1,2})?\s*(?:€|EUR|euros?)?',
        r'(?i)["\'](?:price|rent|monthlyRent|rentalPrice)["\']\s*[:=]\s*["\']?([0-9][0-9 .]*)',
        r'([0-9][0-9 .\u00a0\u202f]{2,})\s*(?:€|EUR|euros?)\s*(?:/\s*(?:mois|month)|par\s*mois)?',
    ]
    candidates=[]
    for pat in patterns:
        for m in re.finditer(pat,text):
            n=_number(m.group(1))
            if n is not None and 50 <= n <= 10000000:candidates.append(n)
    # For a rental page, discard implausible values such as surface/room counts.
    for n in candidates:
        if 100 <= n <= 20000:return n
    return candidates[0] if candidates else None

def _canonical_url(url):
    p=urlparse(url.strip())
    return urlunparse((p.scheme.lower(),p.netloc.lower(),p.path.rstrip('/'),'','',''))

def parse_url(url):
    p=urlparse(url)
    if p.scheme not in ('http','https'):raise ValueError('URL invalide')
    req=Request(url,headers={'User-Agent':'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/151 Safari/537.36','Accept-Language':'fr-FR,fr;q=0.9,en;q=0.8','Accept':'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'})
    try:
        with urlopen(req,timeout=20) as r: raw=r.read(4000000)
    except Exception as e:
        raise ValueError(f'Impossible d’accéder au site ({type(e).__name__}). Le site peut bloquer les robots.')
    text=raw.decode('utf-8','ignore'); q=_Parser(); q.feed(text)
    objs=[o for j in q.jsonld for o in _walk(j)]
    obj=next((o for o in objs if isinstance(o,dict) and (o.get('@type') in ('Apartment','SingleFamilyResidence','Residence','Offer') or 'price' in o or 'offers' in o)),{})
    offers=obj.get('offers') if isinstance(obj.get('offers'),dict) else {}
    title=obj.get('name') or q.meta.get('og:title') or q.meta.get('twitter:title') or q.meta.get('title')
    desc=obj.get('description') or q.meta.get('description') or q.meta.get('og:description') or ''
    price=_find_price(text,q.meta,objs)
    fs=obj.get('floorSize'); surface=_number(fs.get('value') if isinstance(fs,dict) else fs) or _number(obj.get('surface')) or _number(obj.get('area'))
    address=obj.get('address'); address=address if isinstance(address,dict) else {}
    city=address.get('addressLocality') or q.meta.get('addresslocality')
    if not city:
        m=re.search(r'\b(montauban|toulouse|albi|caussade|castelsarrasin)\b',text,re.I); city=m.group(1).title() if m else 'Montauban'
    low=(title or '')+' '+desc+' '+text[:120000]
    rooms=_number(obj.get('numberOfRooms') or obj.get('numberOfBedrooms'))
    if re.search(r'\bstudio\b',low,re.I) or rooms==1: typ='Studio'
    elif re.search(r'\bT1\b',low,re.I): typ='T1'
    elif re.search(r'\bT2\b',low,re.I) or rooms==2: typ='T2'
    elif re.search(r'\bcolocation\b',low,re.I): typ='Colocation'
    else: typ='Appartement'
    furnished=1 if re.search(r'\bmeubl[ée]|furnished\b',low,re.I) else 0
    if not title:title=f'{typ} à louer - {city}'
    if price is None:raise ValueError('Le prix de cette annonce n’est pas accessible dans les données publiques de la page.')
    return {'title':title.strip(),'city':city.strip(),'price':price,'surface':surface or 0,'type':typ,'furnished':furnished,'description':desc.strip()[:5000],'source':p.netloc.lower().replace('www.',''),'source_url':_canonical_url(url)}

@logeo.app.post('/api/import-url')
def import_url():
    try:
        u=logeo.user()
        if not u:return jsonify(error='Connexion requise'),401
        if u['role']!='owner':return jsonify(error='Import réservé aux propriétaires / agences'),403
        payload=request.get_json(silent=True) or {}; url=str(payload.get('url') or '').strip()
        if not url:return jsonify(error='Colle le lien de l’annonce'),400
        data=parse_url(url)
        c=logeo.db()
        try:
            # Canonical URL removes tracking/search parameters so the same Bien'ici ad cannot be imported twice.
            existing=c.execute('SELECT * FROM listings WHERE source_url=?',(data['source_url'],)).fetchone()
            if not existing:
                # Also recognize an older import that kept the query string.
                rows=c.execute('SELECT * FROM listings WHERE source=? AND source_url LIKE ?',(data['source'],data['source_url']+'%')).fetchall()
                existing=rows[0] if rows else None
            if existing:return jsonify(ok=True,duplicate=True,listing=dict(existing))
            cur=c.execute('INSERT INTO listings(title,city,price,surface,type,distance_km,furnished,available_date,source,source_url,description,owner_id,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)',(data['title'],data['city'],data['price'],data['surface'],data['type'],0,data['furnished'],None,data['source'],data['source_url'],data['description'],u['id'],datetime.utcnow().isoformat()))
            c.commit(); row=c.execute('SELECT * FROM listings WHERE id=?',(cur.lastrowid,)).fetchone()
            return jsonify(ok=True,duplicate=False,listing=dict(row))
        finally:c.close()
    except ValueError as e:return jsonify(error=str(e)),422
    except Exception as e:return jsonify(error=f'Erreur LOGEO pendant l’import : {type(e).__name__}'),500

_original_home=logeo.app.view_functions.get('home')
def _home_with_import():
    html=_original_home()
    block='''<div id="ownerUrlImport" class="card" style="border:2px solid #dbe4ff;background:#f8faff"><h3>🔗 Importer une annonce</h3><p class="muted">Colle le lien public d’une annonce Bien’ici, SeLoger, etc. LOGEO récupérera les informations disponibles.</p><div class="grid"><label>Lien de l’annonce<input id="ownerImportUrl" type="url" placeholder="https://www.bienici.com/annonce/..."></label><div style="display:flex;align-items:end"><button type="button" onclick="logeoImportUrl()">📥 Importer automatiquement</button></div></div><p id="ownerImportMsg"></p></div>'''
    html=html.replace('<h3>Nouvelle annonce</h3>',block+'<h3>Nouvelle annonce</h3>',1)
    js='''<script>async function logeoImportUrl(){const i=document.getElementById("ownerImportUrl"),m=document.getElementById("ownerImportMsg"),b=i&&i.value.trim();if(!b){m.textContent="Colle d’abord le lien de l’annonce.";m.className="err";return}m.textContent="Import de l’annonce en cours…";m.className="muted";try{const r=await fetch("/api/import-url",{method:"POST",headers:{"Content-Type":"application/json","Accept":"application/json"},body:JSON.stringify({url:b})});const raw=await r.text();let x;try{x=JSON.parse(raw)}catch(_){throw Error("Réponse serveur invalide (HTTP "+r.status+"). Le serveur LOGEO doit être redéployé.")}if(!r.ok)throw Error(x.error||"Import impossible");m.textContent=x.duplicate?"Cette annonce est déjà dans tes annonces.":"✅ Annonce importée dans Mes annonces !";m.className="ok";i.value="";if(typeof loadOwner==="function")loadOwner()}catch(e){m.textContent="❌ "+e.message;m.className="err"}}</script>'''
    return html.replace('</body>',js+'</body>',1)
if _original_home: logeo.app.view_functions['home']=_home_with_import
