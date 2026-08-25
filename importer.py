import json, re, html as htmlmod
from urllib.request import Request, urlopen
from urllib.parse import urlparse
from html.parser import HTMLParser
from datetime import datetime

class MetaParser(HTMLParser):
    def __init__(self):
        super().__init__(); self.meta={}; self.jsonlds=[]; self.title=[]; self._script_json=False; self._buf=[]
    def handle_starttag(self, tag, attrs):
        a=dict(attrs)
        if tag=='meta' and (a.get('property') or a.get('name')):
            k=a.get('property') or a.get('name'); self.meta[k.lower()]=a.get('content','')
        elif tag=='title': self._buf=[]
        elif tag=='script' and a.get('type','').lower()=='application/ld+json': self._script_json=True; self._buf=[]
    def handle_endtag(self, tag):
        if tag=='title' and self._buf: self.meta['title']=''.join(self._buf).strip(); self._buf=[]
        elif tag=='script' and self._script_json:
            raw=''.join(self._buf).strip()
            if raw:
                try:self.jsonlds.append(json.loads(raw))
                except Exception:pass
            self._script_json=False; self._buf=[]
    def handle_data(self, data):
        if self._script_json or self.meta.get('title') is None: self._buf.append(data)

def _walk(obj):
    if isinstance(obj, dict):
        yield obj
        for v in obj.values(): yield from _walk(v)
    elif isinstance(obj, list):
        for v in obj: yield from _walk(v)

def _num(v):
    if v is None:return None
    m=re.search(r'([0-9][0-9 .\u00a0]*)(?:[,\.]([0-9]+))?',str(v))
    if not m:return None
    s=m.group(1).replace(' ','').replace('\u00a0','').replace('.','')
    dec=m.group(2)
    try:return float(s+(('.'+dec) if dec else ''))
    except:return None

def _first(*vals):
    return next((v for v in vals if v not in (None,'')),None)

def parse_listing(url):
    p=urlparse(url)
    if p.scheme not in ('http','https'): raise ValueError('URL invalide')
    req=Request(url,headers={'User-Agent':'Mozilla/5.0 (compatible; LOGEO/1.0; +https://logeo.app)'})
    with urlopen(req,timeout=15) as r: raw=r.read(2_000_000)
    text=raw.decode('utf-8','ignore'); parser=MetaParser(); parser.feed(text)
    meta=parser.meta; objs=[o for j in parser.jsonlds for o in _walk(j)]
    offer=next((o for o in objs if 'price' in o or o.get('@type') in ('Offer','Apartment','Residence')), {})
    addr=next((o for o in objs if isinstance(o,dict) and ('addressLocality' in o or 'address' in o)), {})
    address=addr.get('address') if isinstance(addr.get('address'),dict) else addr
    offers=offer.get('offers') if isinstance(offer.get('offers'),dict) else offer.get('offers') or {}
    if isinstance(offers,list): offers=offers[0] if offers else {}
    title=_first(offer.get('name'),meta.get('og:title'),meta.get('twitter:title'),meta.get('title'))
    desc=_first(offer.get('description'),meta.get('description'),meta.get('og:description'))
    price=_num(_first(offers.get('price'),offer.get('price'),meta.get('product:price:amount')))
    surface=_num(_first(offer.get('floorSize'),offer.get('surface'),offer.get('area'),meta.get('surface')))
    if isinstance(offer.get('floorSize'),dict): surface=_num(offer['floorSize'].get('value'))
    rooms=_num(_first(offer.get('numberOfRooms'),offer.get('numberOfBedrooms')))
    city=_first(address.get('addressLocality') if isinstance(address,dict) else None,meta.get('addressLocality'))
    if not city:
        m=re.search(r'\b(montauban|toulouse|albi|caussade|castelsarrasin)\b',text,re.I); city=m.group(1).title() if m else 'Montauban'
    low=(title or '')+' '+(desc or '')+' '+text[:100000]
    furnished=1 if re.search(r'\bmeubl[ée]|furnished\b',low,re.I) else 0
    if re.search(r'\bT2\b',low,re.I) or rooms==2: typ='T2'
    elif re.search(r'\bT1\b',low,re.I) or rooms==1: typ='T1'
    elif re.search(r'\bstudio\b',low,re.I): typ='Studio'
    else: typ='Appartement'
    available=None
    m=re.search(r'(?:disponible|disponibilit[ée])[^0-9]*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',low,re.I)
    if m:
        try: available=datetime.strptime(m.group(1).replace('/','-'),'%d-%m-%Y').date().isoformat()
        except: pass
    if not title: title=f'{typ} à louer à {city}'
    if price is None: raise ValueError('Prix non détecté automatiquement')
    if surface is None: surface=0
    return {'title':htmlmod.unescape(title).strip(),'city':city,'price':price,'surface':surface,'type':typ,'distance_km':0,'furnished':furnished,'available_date':available,'source':p.netloc.lower().replace('www.',''),'source_url':url,'description':htmlmod.unescape((desc or '').strip())[:5000]}

def register_import_route(app, db, user_fn):
    from flask import request, jsonify
    @app.post('/api/import-url')
    def import_url():
        u=user_fn()
        if not u:return jsonify(error='Connexion requise'),401
        x=request.json or {}; url=(x.get('url') or '').strip()
        if not url:return jsonify(error='URL manquante'),400
        try:data=parse_listing(url)
        except Exception as e:return jsonify(error=f'Import impossible : {e}'),422
        c=db(); existing=c.execute('SELECT * FROM listings WHERE source_url=?',(data['source_url'],)).fetchone()
        if existing:
            c.close(); return jsonify(ok=True,duplicate=True,listing=dict(existing))
        now=datetime.utcnow().isoformat()
        cur=c.execute('INSERT INTO listings(title,city,price,surface,type,distance_km,furnished,available_date,source,source_url,description,owner_id,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)',(data['title'],data['city'],data['price'],data['surface'],data['type'],0,data['furnished'],data['available_date'],data['source'],data['source_url'],data['description'],u['id'] if u['role']=='owner' else None,now)); c.commit(); lid=cur.lastrowid
        row=c.execute('SELECT * FROM listings WHERE id=?',(lid,)).fetchone(); c.close()
        return jsonify(ok=True,duplicate=False,listing=dict(row))
    return app

register_import_route(__import__('app').app, __import__('app').db, __import__('app').user)
