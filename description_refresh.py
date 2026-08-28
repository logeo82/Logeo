import os,json,re,urllib.parse,urllib.request,html,time
from flask import jsonify
import app as logeo
import listing_enrichment as le
BASE='https://cherchertrouver.immo/api/v1'

def _detail(source,reference):
 key=os.environ.get('CHERCHER_TROUVER_API_KEY','').strip()
 if not key:return {}
 path=f"{BASE}/annonces/{urllib.parse.quote(str(source),safe='')}/{urllib.parse.quote(str(reference),safe='')}"
 for attempt in range(3):
  req=urllib.request.Request(path,headers={'X-Api-Key':key,'Accept':'application/json','User-Agent':'LOGEO/1.4'})
  try:
   with urllib.request.urlopen(req,timeout=25) as r:data=json.loads(r.read().decode('utf-8'))
   if not isinstance(data,dict):return {}
   for k in ('annonce','listing','item','data','result'):
    if isinstance(data.get(k),dict):return data[k]
   return data
  except urllib.error.HTTPError as exc:
   if exc.code!=429 or attempt==2: return {}
   retry_after=exc.headers.get('Retry-After')
   try:delay=min(max(float(retry_after),2.0),15.0)
   except Exception:delay=3.0*(attempt+1)
   print(f'LOGEO: ChercherTrouver rate limit (429), retry {attempt+1}/2 in {delay:.1f}s')
   time.sleep(delay)
  except Exception:
   return {}
 return {}

def _deep(d,names):
 if not isinstance(d,dict):return None
 for n in names:
  v=d.get(n)
  if v not in (None,'',[]):return v
 for v in d.values():
  if isinstance(v,dict):
   x=_deep(v,names)
   if x not in (None,'',[]):return x
 return None

def _description(d):
 names=('description_full','full_description','description_long','long_description','description','descriptif','texte','ad_text','listing_description','description_text','content','body','description_html')
 v=_deep(d,names)
 if isinstance(v,dict):v=_deep(v,('text','html','content','value'))
 text='' if v is None else str(v)
 extras=[]
 for n in ('description_full','full_description','description_long','long_description'):
  x=_deep(d,(n,))
  if x and str(x).strip() and str(x).strip() not in text:extras.append(str(x).strip())
 if extras:text=text.rstrip()+'\n\n'+'\n\n'.join(extras)
 text=re.sub(r'<br\s*/?>','\n',text,flags=re.I)
 text=re.sub(r'</p\s*>','\n\n',text,flags=re.I)
 text=re.sub(r'<[^>]+>','',text)
 return re.sub(r'\n{3,}','\n\n',html.unescape(text)).strip()

def _external_url(d,row):
 u=_deep(d,('external_url','url','source_url'))
 if u and str(u).startswith('http'):return str(u)
 u=row['source_url'] if 'source_url' in row.keys() else None
 return str(u) if u and str(u).startswith('http') else ''

def _external_description(url):
 if not url:return ''
 try:
  req=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0 (compatible; LOGEO/1.0)','Accept':'text/html,application/xhtml+xml'})
  with urllib.request.urlopen(req,timeout=20) as r:raw=r.read(1800000).decode('utf-8','ignore')
  candidates=[]
  for block in re.findall(r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',raw,re.I|re.S):
   try:
    data=json.loads(html.unescape(block));stack=data if isinstance(data,list) else [data]
    while stack:
     x=stack.pop()
     if isinstance(x,dict):
      v=x.get('description')
      if isinstance(v,str) and len(v)>80:candidates.append(v)
      for y in x.values():
       if isinstance(y,(dict,list)):stack.extend(y if isinstance(y,list) else [y])
     elif isinstance(x,list):stack.extend(x)
   except Exception:pass
  for pat in (r'<meta[^>]+(?:name|property)=["\']description["\'][^>]+content=["\'](.*?)["\']',r'<meta[^>]+content=["\'](.*?)["\'][^>]+(?:name|property)=["\']description["\']'):
   for v in re.findall(pat,raw,re.I|re.S):
    v=html.unescape(re.sub(r'<[^>]+>','',v)).strip()
    if len(v)>80:candidates.append(v)
  for m in re.finditer(r'(?i)["\']description["\']\s*:\s*["\']((?:\\.|[^"\']){80,})["\']',raw):
   try:v=json.loads('"'+m.group(1)+'"')
   except Exception:v=html.unescape(m.group(1))
   if len(v)>80:candidates.append(v)
  if not candidates:return ''
  candidates=[re.sub(r'\s+',' ',x).strip() for x in candidates]
  return max(candidates,key=len)
 except Exception as exc:
  print(f'LOGEO external description unavailable: {type(exc).__name__}: {exc}')
  return ''

def enrich_listing_full(listing_id):
 u=logeo.require_role('owner')
 if not u:return jsonify(error='Connexion propriétaire requise'),401
 if u is False:return jsonify(error='Compte étudiant'),403
 c=logeo.db();row=c.execute(logeo.ph('SELECT * FROM listings WHERE id=? AND owner_id=?'),(listing_id,u['id'])).fetchone();c.close()
 if not row:return jsonify(error='Annonce introuvable'),404
 source=row['source'] if 'source' in row.keys() else None;reference=row['source_reference'] if 'source_reference' in row.keys() else None
 if not source or not reference:return jsonify(ok=True,listing=dict(row),enriched=False)
 try:detail=_detail(source,reference)
 except Exception as exc:return jsonify(ok=True,listing=dict(row),enriched=False,error_detail=str(exc))
 if not detail:return jsonify(ok=True,listing=dict(row),enriched=False)
 merged=dict(row);merged.update(detail)
 api_desc=_description(detail);external_desc=_external_description(_external_url(detail,row))
 descriptions=[x for x in (api_desc,external_desc,merged.get('description') or '') if x]
 merged['description']=max(descriptions,key=len) if descriptions else ''
 for k,v in le._derive(merged['description'],merged).items():
  if merged.get(k) in (None,''):merged[k]=v
 updated=le._update(listing_id,merged)
 return jsonify(ok=True,enriched=True,listing=updated)

logeo.app.view_functions['enrich_listing']=enrich_listing_full
print('LOGEO: full description refresh enabled - v4 rate-limit retry')