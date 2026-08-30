"""LOGEO AI Agent: free, source-agnostic listing analysis layer."""
import re, html
from urllib.parse import urlparse
DESCRIPTION_KEYS=("description","description_full","full_description","long_description","description_text","descriptif","body","content","text","value")
def clean_text(v):
    if v is None:return ''
    if isinstance(v,dict):
        for k in DESCRIPTION_KEYS:
            if k in v:
                s=clean_text(v[k])
                if s:return s
        return ''
    if isinstance(v,list):return '\n\n'.join(s for s in (clean_text(x) for x in v) if s)
    s=html.unescape(str(v));s=re.sub(r'<br\s*/?>','\n',s,flags=re.I);s=re.sub(r'</p\s*>','\n\n',s,flags=re.I);s=re.sub(r'<[^>]+>','',s);return re.sub(r'\n{3,}','\n\n',s).strip()
def extract_descriptions(*payloads):
    found=[]
    def walk(x,depth=0):
        if depth>8:return
        if isinstance(x,dict):
            for k,v in x.items():
                if str(k).lower() in DESCRIPTION_KEYS:
                    s=clean_text(v)
                    if s:found.append((len(s),s,str(k)))
                elif isinstance(v,(dict,list)):walk(v,depth+1)
        elif isinstance(x,list):
            for v in x:walk(v,depth+1)
    for p in payloads:walk(p)
    return max(found,key=lambda x:x[0]) if found else (0,'',None)
def analyze(*payloads):
    n,s,source=extract_descriptions(*payloads)
    return {'description':s,'description_length':n,'description_source':source,'preview_502':n==502,'complete':bool(s) and n>502,'warnings':(['description_missing'] if not s else (['possible_preview'] if n<=502 else []))}
def inspect_url(url):
    p=urlparse(url or '')
    return {'valid':p.scheme in ('http','https') and bool(p.netloc),'host':p.netloc,'path':p.path}
