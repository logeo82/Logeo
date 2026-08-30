"""LOGEO AI ENGINE - free, deterministic listing extraction/orchestration.
Keeps source connectors intact; validates, merges and diagnoses listing data.
No paid AI API is required for the core engine.
"""
import re, html, json
from urllib.parse import urlparse

DESCRIPTION_LIMIT_WARNING=502
REQUIRED=('title','price','surface','city')

def clean_text(value):
    if value is None:return ''
    if isinstance(value,(dict,list)):
        if isinstance(value,dict):
            for k in ('text','content','value','description','html'):
                if k in value:
                    v=clean_text(value[k])
                    if v:return v
            return ''
        return '\n\n'.join(filter(None,(clean_text(x) for x in value))).strip()
    s=html.unescape(str(value))
    s=re.sub(r'<br\s*/?>','\n',s,flags=re.I)
    s=re.sub(r'</p\s*>','\n\n',s,flags=re.I)
    s=re.sub(r'<[^>]+>','',s)
    return re.sub(r'\n{3,}','\n\n',s).strip()

def _description_candidates(obj):
    found=[]
    if not isinstance(obj,dict):return found
    exact=('description','description_full','full_description','description_long','long_description','descriptif','description_text','description_html')
    for k in exact:
        if k in obj:
            v=clean_text(obj[k])
            if v:found.append((v,100,k))
    # Recursively inspect common embedded JSON structures, but keep generic
    # body/content below explicit description fields.
    def walk(x,depth=0):
        if depth>6:return
        if isinstance(x,dict):
            for k,v in x.items():
                if str(k).lower() in ('content','body','text','value'):
                    t=clean_text(v)
                    if t:found.append((t,20,str(k)))
                if isinstance(v,(dict,list)):walk(v,depth+1)
        elif isinstance(x,list):
            for v in x:walk(v,depth+1)
    walk(obj)
    return found

def choose_description(*objects):
    candidates=[]
    for obj in objects:candidates.extend(_description_candidates(obj))
    explicit=[x for x in candidates if x[1]>=100]
    pool=explicit or candidates
    if not pool:return '',{'length':0,'truncated_502':False,'source':None}
    value,_,source=max(pool,key=lambda x:len(x[0]))
    return value,{'length':len(value),'truncated_502':len(value)==DESCRIPTION_LIMIT_WARNING,'source':source}

def merge_listing(*objects):
    out={}
    for obj in objects:
        if isinstance(obj,dict):
            for k,v in obj.items():
                if v not in (None,'',[],{}):out[k]=v
    desc,diag=choose_description(*objects)
    if desc:out['description']=desc
    return out,diag

def validate(listing):
    missing=[k for k in REQUIRED if listing.get(k) in (None,'')]
    desc=clean_text(listing.get('description'))
    warnings=[]
    if not desc:warnings.append('description_missing')
    elif len(desc)<=DESCRIPTION_LIMIT_WARNING:warnings.append('description_may_be_preview')
    return {'complete':not missing and bool(desc),'missing':missing,'warnings':warnings,'description_length':len(desc)}

def analyze_url(url):
    p=urlparse(url or '')
    return {'valid':p.scheme in ('http','https') and bool(p.netloc),'host':p.netloc,'path':p.path}
