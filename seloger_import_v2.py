import json, re
from html.parser import HTMLParser
from urllib.request import Request, urlopen
from urllib.parse import urlparse
from flask import request, jsonify
import app as logeo

class P(HTMLParser):
    def __init__(self):
        super().__init__(); self.meta={}; self.jsonld=[]; self.inj=False; self.buf=[]
    def handle_starttag(self,t,a):
        d=dict(a); typ=(d.get('type') or '').lower()
        if t=='meta':
            k=(d.get('property') or d.get('name') or d.get('itemprop') or '').lower()
            if k:self.meta[k]=d.get('content','')
        if t=='script' and typ.startswith('application/ld+json'): self.inj=True; self.buf=[]
    def handle_endtag(self,t):
        if t=='script' and self.inj:
            try:self.jsonld.append(json.loads(''.join(self.buf)))
            except:pass
            self.inj=False
    def handle_data(self,d):
        if self.inj:self.buf.append(d)

def walk(x):
    if isinstance(x,dict):
        yield x
        for v in x.values():yield from walk(v)
    elif isinstance(x,list):
        for v in x:yield from walk(v)

def num(v):
    if v is None:return None
    if isinstance(v,(int,float)):return float(v)
    m=re.search(r'([0-9][0-9 .]*)(?:[,.]([0-9]+))?',str(v).replace('\xa0',' '))
    if not m:return None
    a=m.group(1).replace(' ','').replace('.',''); return float(a+'.'+m.group(2)) if m.group(2) else float(a)

def first(*x):return next((v for v in x if v not in (None,'',[])),None)
def photos(p,raw):
    out=[]; seen=set()
    def add(u):
        if not isinstance(u,str):return
        u=u.strip().replace('\\/','/')
        if u.startswith('//'):u='https:'+u
        if not u.startswith(('http://','https://')) or any(z in u.lower() for z in ('logo','icon','favicon','sprite')):return
        if u not in seen:seen.add(u);out.append(u)
    for k in ('og:image','twitter:image','image'):add(p.meta.get(k))
    for j in p.jsonld:
        for o in walk(j):
            if not isinstance(o,dict):continue
            for k in ('image','images','photo','photos','pictures','media','contentUrl'):
                v=o.get(k)
                for q in v if isinstance(v,list) else [v]:
                    add(q.get('url') or q.get('contentUrl') or q.get('src') if isinstance(q,dict) else q)
    text=raw.decode('utf-8','ignore')
    for m in re.finditer(r'https?:\\?/\\?/[^\"\'<>\s]+?\.(?:jpe?g|png|webp)(?:\?[^\"\'<>\s]*)?',text,re.I):add(m.group(0))
    return out

def parse(url):
    req=Request(url,headers={'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/151 Safari/537.36','Accept-Language':'fr-FR,fr;q=0.9','Accept':'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'})
    with urlopen(req,timeout=25) as r:raw=r.read(12000000)
    p=P();p.feed(raw.decode('utf-8','ignore')); objs=[o for j in p.jsonld for o in walk(j)]
    o=next((x for x in objs if isinstance(x,dict) and (x.get('@type') in ('Apartment','House','Product','Residence','Offer') or 'offers' in x or 'price' in x)),{})
    offers=o.get('offers') if isinstance(o.get('offers'),dict) else {}
    addr=o.get('address') if isinstance(o.get('address'),dict) else {}
    title=first(o.get('name'),p.meta.get('og:title'),p.meta.get('twitter:title'))
    desc=first(o.get('description'),p.meta.get('description'),p.meta.get('og:description'),'')
    price=num(first(offers.get('price'),o.get('price'),p.meta.get('product:price:amount')))
    surface=num(first(o.get('floorSize',{}).get('value') if isinstance(o.get('floorSize'),dict) else None,o.get('surface'),o.get('area')))
    rawtxt=re.sub(r'\s+',' ',re.sub(r'<[^>]+>',' ',raw.decode('utf-8','ignore')))
    if price is None:
        m=re.search(r'(?:loyer|prix|montant)[^0-9]{0,100}([0-9][0-9 .]{2,})\s*€',rawtxt,re.I); price=num(m.group(1)) if m else None
    if surface is None:
        m=re.search(r'(?:surface|superficie)[^0-9]{0,60}([0-9]+(?:[,.][0-9]+)?)\s*m²',rawtxt,re.I); surface=num(m.group(1)) if m else 0
    low=(title or '')+' '+desc+' '+rawtxt[:250000]
    m=re.search(r'\b(\d{5})\b',low); cp=m.group(1) if m else ''
    city=first(addr.get('addressLocality'),p.meta.get('addresslocality'))
    typ='Maison' if re.search(r'\bmaison\b',low,re.I) else ('Studio' if re.search(r'\bstudio\b',low,re.I) else 'Appartement')
    pieces=num(first(re.search(r'\b(\d+)\s*pi[eè]ces?\b',low,re.I).group(1) if re.search(r'\b(\d+)\s*pi[eè]ces?\b',low,re.I) else None))
    chambres=num(first(re.search(r'\b(\d+)\s*chambres?\b',low,re.I).group(1) if re.search(r'\b(\d+)\s*chambres?\b',low,re.I) else None))
    return {'title':title or '', 'description':desc, 'price':price, 'surface':surface or 0, 'city':city or '', 'postal_code':cp, 'type':typ, 'pieces':pieces or 0, 'bedrooms':chambres or 0, 'furnished':1 if re.search(r'\bmeubl[ée]\b',low,re.I) else 0, 'photos':photos(p,raw), 'source_url':url}

@logeo.app.post('/api/seloger-import-v2')
def import_v2():
    u=logeo.user()
    if not u:return jsonify(error='Connexion requise'),401
    if u['role']!='owner':return jsonify(error='Réservé aux propriétaires'),403
    data=request.get_json(silent=True) or {}; url=str(data.get('url') or '').strip()
    if not url:return jsonify(error='URL manquante'),400
    try:return jsonify(ok=True,data=parse(url))
    except Exception as e:return jsonify(error=f'Analyse impossible : {type(e).__name__}'),422
