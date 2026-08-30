import re,html
from fastapi import FastAPI
from pydantic import BaseModel
import httpx
from bs4 import BeautifulSoup
from urllib.parse import urlparse
app=FastAPI(title='LOGEO AI Engine')
class Req(BaseModel): url:str

def clean(s):
 s=html.unescape(s or '');s=BeautifulSoup(s,'html.parser').get_text('\n');return re.sub(r'\n{3,}','\n\n',s).strip()
def candidates(data):
 out=[]
 def walk(x):
  if isinstance(x,dict):
   for k,v in x.items():
    if str(k).lower() in ('description','description_full','full_description','long_description','description_text','descriptif','body','content','text') and isinstance(v,str):
     t=clean(v)
     if t:out.append((len(t),t,k))
    elif isinstance(v,(dict,list)):walk(v)
  elif isinstance(x,list):
   for v in x:walk(v)
 walk(data);return sorted(out,reverse=True)
@app.get('/health')
def health():return {'ok':True,'service':'logeo-ai-engine'}
@app.post('/extract')
async def extract(r:Req):
 p=urlparse(r.url)
 if p.scheme not in ('http','https') or not p.netloc:return {'ok':False,'error':'URL invalide'}
 try:
  async with httpx.AsyncClient(follow_redirects=True,timeout=20,headers={'User-Agent':'Mozilla/5.0 (compatible; LOGEO-AI/1.0)'}) as c:
   z=await c.get(r.url);z.raise_for_status();raw=z.text
  soup=BeautifulSoup(raw,'html.parser'); vals=[]
  for s in soup.select('script[type="application/ld+json"]'):
   try:
    import json;vals.append(json.loads(s.string or s.get_text()))
   except Exception:pass
  cs=candidates(vals)
  meta=[]
  for m in soup.find_all('meta'):
   n=(m.get('name') or m.get('property') or '').lower();v=m.get('content') or ''
   if 'description' in n and v:meta.append((len(clean(v)),clean(v),n))
  cs+=meta;cs.sort(reverse=True)
  desc=cs[0][1] if cs else ''
  return {'ok':True,'url':str(z.url),'description':desc,'description_length':len(desc),'possible_preview':len(desc)<=502 if desc else False,'structured_candidates':len(cs)}
 except Exception as e:return {'ok':False,'error':str(e)}
