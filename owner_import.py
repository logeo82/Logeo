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
            if key:self.meta[key]=a.get('content','')
        elif tag=='title':self._buf=[]
        elif tag=='script' and a.get('type','').lower()=='application/ld+json':self._json=True;self._buf=[]
    def handle_endtag(self, tag):
        if tag=='title' and self._buf:self.meta['title']=''.join(self._buf).strip();self._buf=[]
        elif tag=='script' and self._json:
            raw=''.join(self._buf).strip()
            if raw:
                try:self.jsonld.append(json.loads(raw))
                except Exception:pass
            self._json=False;self._buf=[]
    def handle_data(self,data):
        if self._json or 'title' not in self.meta:self._buf.append(data)

def _walk(x):
    if isinstance(x,dict):
        yield x
        for v in x.values():yield from _walk(v)
    elif isinstance(x,list):
        for v in x:yield from _walk(v)

def _number(v):
    if v is None:return None
    if isinstance(v,(int,float)):return float(v)
    m=re.search(r'([0-9][0-9 .\u00a0]*)(?:[,\.]([0-9]+))?',str(v))
    if not m:return None
    a=m.group(1).replace(' ','').replace('\u00a0','').replace('.','')
    try:return float(a+(('.'+m.group(2)) if m.group(2) else ''))
    except:return None

def _find_key(x,keys):
    for o in _walk(x):
        if isinstance(o,dict):
            for k in keys:
                if k in o and o[k] not in (None,'',[]):
                    n=_number(o[k])
                    if n is not None:return n
    return None

def _canonical_url(url):
    p=urlparse(url);return f'{p.scheme.lower()}://{p.netloc.lower()}{p.path.rstrip("/")}'

def _fetch_json(url):
    req=Request(url,headers={'User-Agent':'Mozilla/5.0','Accept':'application/json,text/plain,*/*','Referer':'https://www.bienici.com/'})
    with urlopen(req,timeout=20) as r:return json.loads(r.read().decode('utf-8','ignore'))

def _extract_photos(data):
    """Collect public image URLs from structured portal data without inventing URLs."""
    found=[]; seen=set()
    keys={'photos','images','pictures','image','picture','media','photoUrls','imageUrls','picturesUrls'}
    for o in _walk(data):
        if not isinstance(o,dict):continue
        for k,v in o.items():
            if str(k).lower() not in keys:continue
            vals=v if isinstance(v,list) else [v]
            for item in vals:
                if isinstance(item,dict):
                    candidates=[item.get(x) for x in ('url','src','large','medium','original','imageUrl','photoUrl')]
                else:candidates=[item]
                for u in candidates:
                    if isinstance(u,str) and u.startswith(('http://','https://')) and re.search(r'\.(?:jpe?g|png|webp)(?:[?#].*)?$',u,re.I):
                        if u not in seen:seen.add(u);found.append(u)
    return found[:30]

def _bienici_detail(url):
    p=urlparse(url)
    if 'bienici.com' not in p.netloc.lower():return None
    slug=p.path.rstrip('/').split('/')[-1]
    if not slug:return None
    for endpoint in ('https://www.bienici.com/realEstateAd.json?id='+slug,
                     'https://www.bienici.com/realEstateAds-one.json?onlyRealEstateAd='+slug):
        try:
            data=_fetch_json(endpoint);objs=list(_walk(data))
            ad=next((o for o in objs if isinstance(o,dict) and any(k in o for k in ('price','monthlyRent','surfaceArea','adId'))),None)
            if not ad:continue
            price=_number(ad.get('price')) or _number(ad.get('monthlyRent'))
            if price is None:price=_find_key(data,('price','monthlyRent','rent','amount'))
            if price is None:continue
            surface=_number(ad.get('surfaceArea')) or _number(ad.get('surface')) or _find_key(ad,('surfaceArea','surface')) or 0
            city=ad.get('city') or ad.get('cityName') or ''
            title=ad.get('title') or ad.get('description') or 'Annonce Bien’ici'
            desc=ad.get('description') or ''
            typ=ad.get('propertyType') or 'Appartement'
            photos=_extract_photos(data)
            return {'title':str(title).strip(),'city':str(city).strip() or 'Montauban','price':price,'surface':surface,'type':str(typ),'furnished':1 if re.search(r'(?i)meubl',str(ad)) else 0,'description':str(desc)[:5000],'source':'bienici.com','source_url':_canonical_url(url),'photos':json.dumps(photos,ensure_ascii=False)}
        except Exception:
            continue
    return None

def parse_url(url):
    p=urlparse(url)
    if p.scheme not in ('http','https'):raise ValueError('URL invalide')
    if 'bienici.com' in p.netloc.lower():
        detail=_bienici_detail(url)
        if detail:return detail
    req=Request(url,headers={'User-Agent':'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/151 Safari/537.36','Accept-Language':'fr-FR,fr;q=0.9,en;q=0.8','Accept':'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'})
    try:
        with urlopen(req,timeout=20) as r:raw=r.read(6000000)
    except Exception as e:raise ValueError(f'Impossible d’accéder au site ({type(e).__name__}). Le site peut bloquer les robots.')
    text=raw.decode('utf-8','ignore');q=_Parser();q.feed(text)
    objs=[o for j in q.jsonld for o in _walk(j)]
    obj=next((o for o in objs if isinstance(o,dict) and (o.get('@type') in ('Apartment','SingleFamilyResidence','Residence','Offer') or 'price' in o or 'offers' in o)),{})
    offers=obj.get('offers') if isinstance(obj.get('offers'),dict) else {}
    title=obj.get('name') or q.meta.get('og:title') or q.meta.get('twitter:title') or q.meta.get('title')
    desc=obj.get('description') or q.meta.get('description') or q.meta.get('og:description') or ''
    price=_number(offers.get('price') or obj.get('price') or q.meta.get('product:price:amount'))
    fs=obj.get('floorSize');surface=_number(fs.get('value') if isinstance(fs,dict) else fs) or _number(obj.get('surface')) or _number(obj.get('area')) or 0
    address=obj.get('address');address=address if isinstance(address,dict) else {}
    city=address.get('addressLocality') or q.meta.get('addresslocality') or 'Montauban'
    if price is None:raise ValueError('Le portail ne fournit pas le prix dans ses données publiques accessibles à LOGEO. Un connecteur compatible est nécessaire.')
    photos=_extract_photos(q.jsonld)
    return {'title':(title or f'Appartement à louer - {city}').strip(),'city':city.strip(),'price':price,'surface':surface,'type':'Appartement','furnished':1 if re.search(r'(?i)meubl',(title or '')+' '+desc) else 0,'description':desc.strip()[:5000],'source':p.netloc.lower().replace('www.',''),'source_url':_canonical_url(url),'photos':json.dumps(photos,ensure_ascii=False)}

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
            # Safe migration: older databases do not have the optional photo field.
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
