import os,json,re,urllib.parse,urllib.request
from flask import jsonify
import app as logeo
import listing_enrichment as le

BASE='https://cherchertrouver.immo/api/v1'

def _detail(source,reference):
 key=os.environ.get('CHERCHER_TROUVER_API_KEY','').strip()
 if not key:return {}
 path=f"{BASE}/annonces/{urllib.parse.quote(str(source),safe='')}/{urllib.parse.quote(str(reference),safe='')}"
 req=urllib.request.Request(path,headers={'X-Api-Key':key,'Accept':'application/json','User-Agent':'LOGEO/1.4'})
 with urllib.request.urlopen(req,timeout=25) as r:data=json.loads(r.read().decode('utf-8'))
 if not isinstance(data,dict):return {}
 for k in ('annonce','listing','item','data','result'):
  if isinstance(data.get(k),dict):return data[k]
 return data

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
 return re.sub(r'\n{3,}','\n\n',text).strip()

def enrich_listing_full(listing_id):
 u=logeo.require_role('owner')
 if not u:return jsonify(error='Connexion propriétaire requise'),401
 if u is False:return jsonify(error='Compte étudiant'),403
 c=logeo.db();row=c.execute(logeo.ph('SELECT * FROM listings WHERE id=? AND owner_id=?'),(listing_id,u['id'])).fetchone();c.close()
 if not row:return jsonify(error='Annonce introuvable'),404
 source=row['source'] if 'source' in row.keys() else None
 reference=row['source_reference'] if 'source_reference' in row.keys() else None
 if not source or not reference:return jsonify(ok=True,listing=dict(row),enriched=False)
 try:detail=_detail(source,reference)
 except Exception as exc:return jsonify(ok=True,listing=dict(row),enriched=False,error_detail=str(exc))
 if not detail:return jsonify(ok=True,listing=dict(row),enriched=False)
 merged=dict(row);merged.update(detail)
 merged['description']=_description(detail) or merged.get('description') or ''
 for k,v in le._derive(merged['description'],merged).items():
  if merged.get(k) in (None,''):merged[k]=v
 updated=le._update(listing_id,merged)
 return jsonify(ok=True,enriched=True,listing=updated)

# Replace the existing Flask view function while keeping its already-registered URL rule.
logeo.app.view_functions['enrich_listing']=enrich_listing_full
print('LOGEO: full description refresh enabled')
