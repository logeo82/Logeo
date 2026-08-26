import json, os, re
from html.parser import HTMLParser
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from flask import Flask, request, jsonify, render_template_string

app = Flask(__name__)
LOGEO_URL = os.environ.get("LOGEO_URL", "").rstrip("/")
TOKEN = os.environ.get("LOGEO_IMPORT_TOKEN", "")

class Parser(HTMLParser):
    def __init__(self):
        super().__init__(); self.meta={}; self.jsonld=[]; self.in_json=False; self.buf=[]; self.in_title=False; self.title=[]
    def handle_starttag(self, tag, attrs):
        a=dict(attrs)
        if tag == "meta":
            k=(a.get("property") or a.get("name") or a.get("itemprop") or "").lower()
            if k: self.meta[k]=a.get("content", "")
        elif tag == "title": self.in_title=True; self.title=[]
        elif tag == "script" and a.get("type", "").lower().split(";")[0].strip()=="application/ld+json": self.in_json=True; self.buf=[]
    def handle_endtag(self, tag):
        if tag=="title":
            self.meta["title"]="".join(self.title).strip(); self.in_title=False
        elif tag=="script" and self.in_json:
            raw="".join(self.buf).strip()
            if raw:
                try: self.jsonld.append(json.loads(raw))
                except Exception: pass
            self.in_json=False; self.buf=[]
    def handle_data(self, data):
        if self.in_json: self.buf.append(data)
        elif self.in_title: self.title.append(data)

def walk(x):
    if isinstance(x, dict):
        yield x
        for v in x.values(): yield from walk(v)
    elif isinstance(x, list):
        for v in x: yield from walk(v)

def first(*v): return next((x for x in v if x not in (None,"",[])), None)

def number(v):
    if v is None: return None
    if isinstance(v,(int,float)): return float(v)
    s=str(v).replace("\xa0"," ").strip()
    # Prefer a French/European monetary number and avoid interpreting IDs as prices.
    m=re.search(r"([0-9]{2,}(?:[ .][0-9]{3})*(?:[,.][0-9]{1,2})?)", s)
    if not m: return None
    n=m.group(1).replace(" ","")
    if "." in n and "," in n: n=n.replace(".","").replace(",",".")
    elif n.count(".")==1 and len(n.rsplit(".",1)[1])==3: n=n.replace(".","")
    else: n=n.replace(",",".")
    try:return float(n)
    except Exception:return None

def canonical(url):
    p=urlparse(url); return f"{p.scheme.lower()}://{p.netloc.lower()}{p.path.rstrip('/')}"

def extract_photos(p,text):
    found=[]; seen=set()
    def add(u):
        if not isinstance(u,str): return
        u=u.strip().replace("\\/","/")
        if u.startswith("//"): u="https:"+u
        if not u.startswith(("http://","https://")): return
        low=u.lower()
        if any(x in low for x in ("logo","icon","favicon","sprite","avatar")): return
        if u not in seen: seen.add(u); found.append(u)
    for k in ("og:image","twitter:image","image","og:image:url","twitter:image:src"): add(p.meta.get(k))
    for root in p.jsonld:
        for o in walk(root):
            if not isinstance(o,dict): continue
            for k in ("image","images","photo","photos","pictures","media","contentUrl"):
                v=o.get(k)
                for item in (v if isinstance(v,list) else [v]):
                    if isinstance(item,dict):
                        for key in ("url","contentUrl","src","imageUrl","photoUrl"): add(item.get(key))
                    else: add(item)
    # Catch image URLs embedded in page state/HTML, including escaped JSON URLs.
    for m in re.finditer(r'https?:\\?/\\?/[^\"\'<>\s]+?\\.(?:jpe?g|png|webp)(?:\\?[^\"\'<>\s]*)?',text,re.I): add(m.group(0))
    return found[:50]

def extract(url, raw):
    text=raw.decode("utf-8","ignore"); p=Parser(); p.feed(text)
    objs=[o for j in p.jsonld for o in walk(j)]
    candidates=[o for o in objs if isinstance(o,dict)]
    obj=next((o for o in candidates if "offers" in o or "price" in o or o.get("@type") in ("Apartment","Residence","Offer","Product","RealEstateListing")),{})
    offers=obj.get("offers") if isinstance(obj.get("offers"),dict) else {}
    title=first(obj.get("name"),p.meta.get("og:title"),p.meta.get("twitter:title"),p.meta.get("title"))
    desc=first(obj.get("description"),p.meta.get("description"),p.meta.get("og:description"),"")
    price=number(first(offers.get("price"),offers.get("lowPrice"),obj.get("price"),p.meta.get("product:price:amount"),p.meta.get("price"),p.meta.get("og:price:amount")))
    surface=number(first(obj.get("surface"),obj.get("area"),p.meta.get("surface"),p.meta.get("property:surface")))
    if surface is None and isinstance(obj.get("floorSize"),dict): surface=number(obj["floorSize"].get("value"))
    visible=re.sub(r"<script[^>]*>.*?</script>|<style[^>]*>.*?</style>"," ",text,flags=re.I|re.S)
    visible=re.sub(r"<[^>]+>"," ",visible); visible=re.sub(r"\s+"," ",visible)
    # Price fallbacks cover rendered/embedded French text and common portal keys.
    if price is None:
        patterns=[
            r'(?:prix(?:\s+de\s+vente)?|montant|loyer|vente)[^0-9]{0,120}([0-9][0-9 .]{2,}(?:,[0-9]{1,2})?)\s*€',
            r'([0-9][0-9 .]{2,}(?:,[0-9]{1,2})?)\s*€\s*(?:/\s*mois|par mois)',
            r'"(?:price|salePrice|sale_price|amount|priceValue|prix|prixVente|prix_vente)"\s*[:=]\s*"?([0-9][0-9 .]*(?:[,.][0-9]+)?)',
            r'\b(?:price|salePrice|sale_price|amount|prix|prixVente|prix_vente)\b\s*[:=]\s*([0-9][0-9 .]*(?:[,.][0-9]+)?)'
        ]
        for pat in patterns:
            m=re.search(pat,text,re.I|re.S)
            if m:
                price=number(m.group(1))
                if price is not None: break
    if surface is None:
        m=re.search(r'(?:surface|superficie|livingArea)[^0-9]{0,50}([0-9]+(?:[,.][0-9]+)?)\s*m²',visible,re.I) or re.search(r'([0-9]+(?:[,.][0-9]+)?)\s*m²',visible,re.I)
        if m: surface=number(m.group(1))
    address=obj.get("address")
    city=address.get("addressLocality") if isinstance(address,dict) else None
    if not city:
        m=re.search(r"\b(montauban|toulouse|albi|caussade|castelsarrasin|moissac)\b",visible,re.I); city=m.group(1).title() if m else "Montauban"
    low=(title or "")+" "+desc+" "+visible[:150000]
    typ="Studio" if re.search(r"\bstudio\b",low,re.I) else ("T2" if re.search(r"\bT2\b",low,re.I) else ("T1" if re.search(r"\bT1\b",low,re.I) else "Appartement"))
    furnished=1 if re.search(r"\bmeubl[ée]|furnished\b",low,re.I) else 0
    photos=extract_photos(p,text)
    if price is None: raise ValueError("Le prix n’est pas exposé dans les données publiques accessibles.")
    return {"title":str(title or f"{typ} à louer à {city}").strip(),"city":str(city).strip(),"price":price,"surface":surface or 0,"type":typ,"furnished":furnished,"description":str(desc).strip()[:10000],"source":urlparse(url).netloc.lower().replace("www.",""),"source_url":canonical(url),"photos":photos}

def fetch_listing(url):
    p=urlparse(url)
    if p.scheme not in ("http","https"): raise ValueError("URL invalide")
    req=Request(url,headers={"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/151 Safari/537.36","Accept-Language":"fr-FR,fr;q=0.9,en;q=0.8","Accept":"text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"})
    try:
        with urlopen(req,timeout=30) as r: raw=r.read(10000000)
    except (HTTPError,URLError,TimeoutError) as e: raise ValueError(f"Portail inaccessible: {type(e).__name__}")
    return extract(url,raw)

def push_to_logeo(data):
    if not LOGEO_URL or not TOKEN: raise RuntimeError("LOGEO_URL ou LOGEO_IMPORT_TOKEN manquant")
    body=json.dumps(data).encode()
    req=Request(LOGEO_URL+"/api/integrations/import-listing",data=body,method="POST",headers={"Content-Type":"application/json","X-Logeo-Import-Token":TOKEN})
    try:
        with urlopen(req,timeout=30) as r: return json.loads(r.read().decode())
    except HTTPError as e:
        detail=e.read().decode("utf-8","ignore")
        raise RuntimeError(f"LOGEO HTTP {e.code}: {detail[:500]}")

@app.get("/health")
def health(): return jsonify(ok=True, logeo_configured=bool(LOGEO_URL and TOKEN))

@app.get("/")
def home():
    return render_template_string('''<!doctype html><html lang="fr"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Chercher-Trouver</title><style>body{font-family:system-ui;margin:0;background:#f5f7fa;color:#111827}.box{max-width:760px;margin:8vh auto;padding:28px;background:#fff;border-radius:20px;box-shadow:0 10px 35px #0001}input{width:100%;box-sizing:border-box;padding:14px;border:1px solid #d0d5dd;border-radius:10px;font-size:16px}button{margin-top:12px;padding:14px 18px;border:0;border-radius:10px;background:#111827;color:#fff;font-weight:800;width:100%}.muted{color:#667085}.ok{color:#087443}.err{color:#b42318;white-space:pre-wrap}</style><div class="box"><h1>🔎 Chercher-Trouver</h1><p class="muted">Colle le lien public d'une annonce immobilière : les données publiques, le prix et les photos disponibles sont analysés puis transmis à LOGEO.</p><input id="url" placeholder="https://www.bienici.com/annonce/..."/><button onclick="go()">Analyser et déposer dans LOGEO</button><p id="msg"></p><pre id="result"></pre></div><script>async function go(){let u=document.getElementById('url').value.trim(),m=document.getElementById('msg'),r=document.getElementById('result');if(!u){m.textContent='Colle un lien.';m.className='err';return}m.textContent='Analyse en cours…';m.className='muted';r.textContent='';try{let x=await fetch('/api/import',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({url:u})});let d=await x.json();if(!x.ok)throw Error(d.error||'Import impossible');m.textContent=d.pushed?'✅ Annonce déposée dans LOGEO':'⚠️ Annonce analysée';m.className=d.pushed?'ok':'muted';r.textContent=JSON.stringify(d,null,2)}catch(e){m.textContent='❌ '+e.message;m.className='err'}}</script></html>''')

@app.post("/api/import")
def import_api():
    x=request.get_json(silent=True) or {}; url=str(x.get("url") or "").strip()
    if not url: return jsonify(error="URL manquante"),400
    try:
        data=fetch_listing(url); pushed=push_to_logeo(data)
        return jsonify(ok=True,pushed=True,listing=data,logeo=pushed)
    except ValueError as e: return jsonify(error=str(e)),422
    except Exception as e: return jsonify(error=str(e)),500

if __name__ == "__main__":
    from waitress import serve
    serve(app,host="0.0.0.0",port=int(os.environ.get("PORT","8080")))
