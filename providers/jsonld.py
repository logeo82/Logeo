import json
from html.parser import HTMLParser
from urllib.request import Request, urlopen
from aggregator import Listing, clean_text

class _JSONLD(HTMLParser):
    def __init__(self): super().__init__(); self.inside=False; self.buf=[]; self.docs=[]
    def handle_starttag(self, tag, attrs):
        if tag.lower()=='script' and dict(attrs).get('type','').lower()=='application/ld+json': self.inside=True; self.buf=[]
    def handle_endtag(self, tag):
        if tag.lower()=='script' and self.inside:
            try: self.docs.append(json.loads(''.join(self.buf)))
            except Exception: pass
            self.inside=False
    def handle_data(self, data):
        if self.inside: self.buf.append(data)

class JsonLdProvider:
    name='jsonld'
    def fetch(self,url):
        req=Request(url,headers={'User-Agent':'Mozilla/5.0 (compatible; Logeo/1.0)'})
        html=urlopen(req,timeout=12).read().decode('utf-8','ignore')
        p=_JSONLD(); p.feed(html)
        docs=p.docs
        flat=[]
        for d in docs: flat.extend(d if isinstance(d,list) else [d])
        obj=next((x for x in flat if isinstance(x,dict) and ('offers' in x or 'description' in x)),{})
        offers=obj.get('offers') or {}
        if isinstance(offers,list): offers=offers[0] if offers else {}
        price=offers.get('price')
        try: price=float(price) if price is not None else None
        except Exception: price=None
        return Listing(source=self.name,source_url=url,title=clean_text(obj.get('name')),description=clean_text(obj.get('description')),price=price,photos=[x for x in (obj.get('image') if isinstance(obj.get('image'),list) else [obj.get('image')]) if x],raw=obj,confidence=.7)
