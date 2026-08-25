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
        super().__init__(); self.meta={}; self.jsonld=[]; self._json=False; self._buf=[]
    def handle_starttag(self, tag, attrs):
        a=dict(attrs)
        if tag=='meta':
            key=(a.get('property') or a.get('name') or '').lower()
            if key: self.meta[key]=a.get('content','')
        elif tag=='script' and a.get('type','').lower()=='application/ld+json':
            self._json=True; self._buf=[]
    def handle_endtag(self, tag):
        if tag=='script' and self._json:
            raw=''.join(self._buf).strip()
            if raw:
                try:self.jsonld.append(json.loads(raw))
                except Exception:pass
            self._json=False; self._buf=[]
    def handle_data(self, data):
        if self._json:self._buf.append(data)

def _walk(x):
    if isinstance(x,dict):
        yield x
        for v in x.values(): yield from _walk(v)
    elif isinstance(x,list):
        for v in x: yield from _walk(v)

def _number(v):
    if v is None:return None
    m=re.search(r'([0-9][0-9 .\u00a0]*)(?:[,\.]([0-9]+))?',str(v))
    if not m:return None
    a=m.group(1).replace(' ','').replace('\u00a0','').replace('.','')
    try:return float(a+(('.'+m.group(2)) if m.group(2) else ''))
    except:return None

def parse_url(url):
    p=urlparse(url)
    if p.scheme not in ('http','https'):raise ValueError('URL invalide')
    req=Request(url,headers={'User-Agent':'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/151 Safari/537.36'})
    with urlopen(req,timeout=20) as r: raw=r.read(4000000)
    text=raw.decode('utf-8','ignore'); q=_Parser(); q.feed(text)
    objs=[o for j in q.jsonld for o in _walk(j)]
    obj=next((o for o in objs if isinstance(o,dict) and (o.get('@type') in ('Apartment','SingleFamilyResidence','Residence','Offer') or 'price' in o or 'offers' in o)),{})
    offers=obj.get('offers') if isinstance(obj.get('offers'),dict) else {}
    title=obj.get('name') or q.meta.get('og:title') or q.meta.get('twitter:title') or q.meta.get('title')
    desc=obj.get('description') or q.meta.get('description') or q.meta.get('og:description') or ''
    price=_number(offers.get('price') or obj.get('price') or q.meta.get('product:price:amount'))
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
    else: typ='Studio'
    furnished=1 if re.search(r'\bmeubl[ée]|furnished\b',low,re.I) else 0
    if not title:title=f'{typ} à louer - {city}'
    if price is None:raise ValueError('Le site ne fournit pas automatiquement le prix')
    return {'title':title.strip(),'city':city.strip(),'price':price,'surface':surface or 0,'type':typ,'furnished':furnished,'description':desc.strip()[:5000],'source':p.netloc.lower().replace('www.',''),'source_url':url}

@logeo.app.post('/api/import-url')
def import_url():
    u=logeo.user()
    if not u:return jsonify(error='Connexion requise'),401
    if u['role']!='owner':return jsonify(error='Import réservé aux propriétaires / agences'),403
    url=(request.json or {}).get('url','').strip()
    if not url:return jsonify(error='Colle le lien de l’annonce'),400
    try:data=parse_url(url)
    except Exception as e:return jsonify(error=f'Import impossible : {e}'),422
    c=logeo.db()
    existing=c.execute('SELECT * FROM listings WHERE source_url=?',(url,)).fetchone()
    if existing:
        c.close(); return jsonify(ok=True,duplicate=True,listing=dict(existing))
    cur=c.execute('INSERT INTO listings(title,city,price,surface,type,distance_km,furnished,available_date,source,source_url,description,owner_id,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)',(data['title'],data['city'],data['price'],data['surface'],data['type'],0,data['furnished'],None,data['source'],url,data['description'],u['id'],datetime.utcnow().isoformat()))
    c.commit(); row=c.execute('SELECT * FROM listings WHERE id=?',(cur.lastrowid,)).fetchone(); c.close()
    return jsonify(ok=True,duplicate=False,listing=dict(row))

_original_home=logeo.app.view_functions.get('home')
def _home_with_import():
    html=_original_home()
    block='''<div id="ownerUrlImport" class="card" style="border:2px solid #dbe4ff;background:#f8faff"><h3>🔗 Importer une annonce</h3><p class="muted">Colle le lien public d’une annonce Bien’ici, SeLoger, etc. LOGEO récupérera les informations disponibles.</p><div class="grid"><label>Lien de l’annonce<input id="ownerImportUrl" type="url" placeholder="https://www.bienici.com/annonce/..."></label><div style="display:flex;align-items:end"><button type="button" onclick="logeoImportUrl()">📥 Importer automatiquement</button></div></div><p id="ownerImportMsg"></p></div>'''
    html=html.replace('<h3>Nouvelle annonce</h3>',block+'<h3>Nouvelle annonce</h3>',1)
    js='''<script>async function logeoImportUrl(){const i=document.getElementById("ownerImportUrl"),m=document.getElementById("ownerImportMsg"),b=i&&i.value.trim();if(!b){m.textContent="Colle d’abord le lien de l’annonce.";m.className="err";return}m.textContent="Import de l’annonce en cours…";m.className="muted";try{const r=await fetch("/api/import-url",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({url:b})}),x=await r.json();if(!r.ok)throw Error(x.error||"Import impossible");m.textContent=x.duplicate?"Cette annonce est déjà dans tes annonces.":"✅ Annonce importée dans Mes annonces !";m.className="ok";i.value="";if(typeof loadOwner==="function")loadOwner()}catch(e){m.textContent=e.message;m.className="err"}}</script>'''
    return html.replace('</body>',js+'</body>',1)
if _original_home: logeo.app.view_functions['home']=_home_with_import
