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
  req=urllib.request.Request(path,headers={'X-Api-Key':key,'Accept':'application/json','User-Agent':'LOGEO/1.5'})
  try:
   with urllib.request.urlopen(req,timeout=25) as r:data=json.loads(r.read().decode('utf-8'))
   if not isinstance(data,dict):return {}
   for k in ('annonce','listing','item','data','result'):
    if isinstance(data.get(k),dict):return data[k]
   return data
  except urllib.error.HTTPError as exc:
   if exc.code!=429 or attempt==2:return {}
   retry_after=exc.headers.get('Retry-After')
   try:delay=min(max(float(retry_after),2.0),15.0)
   except Exception:delay=3.0*(attempt+1)
   print(f'LOGEO: ChercherTrouver rate limit (429), retry {attempt+1}/2 in {delay:.1f}s')
   time.sleep(delay)
  except Exception:return {}
 return {}

def _description(d):
 names={'description','description_full','full_description','description_long','long_description','descriptif','texte','ad_text','listing_description','description_text','content','body','description_html'}
 found=[]
 def walk(x):
  if isinstance(x,dict):
   for k,v in x.items():
    kl=str(k).lower()
    if kl in names and isinstance(v,str) and v.strip():found.append(v)
    elif kl in names and isinstance(v,dict):
     for kk in ('text','html','content','value'):
      if isinstance(v.get(kk),str) and v.get(kk).strip():found.append(v[kk])
    if isinstance(v,(dict,list)):walk(v)
  elif isinstance(x,list):
   for v in x:walk(v)
 walk(d)
 cleaned=[]
 for v in found:
  v=re.sub(r'<br\s*/?>','\n',v,flags=re.I)
  v=re.sub(r'</p\s*>','\n\n',v,flags=re.I)
  v=re.sub(r'<[^>]+>','',v)
  v=re.sub(r'\n{3,}','\n\n',html.unescape(v)).strip()
  if v and v not in cleaned:cleaned.append(v)
 result=max(cleaned,key=len) if cleaned else ''
 return result

def _duplicate_details(detail,source,reference):
 sources=detail.get('sources') if isinstance(detail,dict) else None
 if not isinstance(sources,list):return []
 out=[]
 seen={(str(source),str(reference))}
 for s in sources:
  if not isinstance(s,dict):continue
  src=str(s.get('source') or '').strip();ref=str(s.get('reference') or '').strip()
  if not src or not ref or (src,ref) in seen:continue
  seen.add((src,ref))
  # Free tier is limited to 1 request/sec; space duplicate detail calls.
  time.sleep(1.1)
  d=_detail(src,ref)
  if d:
   desc=_description(d)
   if desc:
    print(f'LOGEO: duplicate source {src}/{ref} description length={len(desc)}')
    out.append((desc,d))
 return out

def enrich_listing_full(listing_id):
 u=logeo.require_role('owner')
 if not u:return jsonify(error='Connexion propriétaire requise'),401
 if u is False:return jsonify(error='Compte étudiant'),403
 c=logeo.db();row=c.execute(logeo.ph('SELECT * FROM listings WHERE id=? AND owner_id=?'),(listing_id,u['id'])).fetchone();c.close()
 if not row:return jsonify(error='Annonce introuvable'),404
 source=row['source'] if 'source' in row.keys() else None;reference=row['source_reference'] if 'source_reference' in row.keys() else None
 if not source or not reference:return jsonify(ok=True,listing=dict(row),enriched=False)
 detail=_detail(source,reference)
 if not detail:return jsonify(ok=True,listing=dict(row),enriched=False,error_detail='Détail Chercher-Trouver indisponible')
 merged=dict(row);merged.update(detail)
 candidates=[(_description(detail),detail)]
 candidates.extend(_duplicate_details(detail,source,reference))
 current=str(merged.get('description') or '').strip()
 if current:candidates.append((current,{}))
 candidates=[x for x in candidates if x[0]]
 best,best_detail=max(candidates,key=lambda x:len(x[0])) if candidates else ('',{})
 merged['description']=best
 # Keep useful fields from the duplicate source that supplied the fuller text.
 if best_detail:
  for k,v in best_detail.items():
   if merged.get(k) in (None,'',[]):merged[k]=v
 for k,v in le._derive(merged['description'],merged).items():
  if merged.get(k) in (None,''):merged[k]=v
 updated=le._update(listing_id,merged)
 print(f'LOGEO: description refresh complete listing={listing_id} length={len(best)}')
 return jsonify(ok=True,enriched=True,description_length=len(best),listing=updated)

logeo.app.view_functions['enrich_listing']=enrich_listing_full
print('LOGEO: full description refresh enabled - v6 duplicate-source descriptions')
