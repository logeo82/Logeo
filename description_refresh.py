import os,json,re,urllib.parse,urllib.request,urllib.error,html,time
from flask import jsonify
import app as logeo
import listing_enrichment as le

BASE='https://cherchertrouver.immo/api/v1'

# The search endpoint may expose a shortened preview. The description must
# ALWAYS be read from the single detail endpoint for the exact listing.
def _detail(source,reference):
    key=os.environ.get('CHERCHER_TROUVER_API_KEY','').strip()
    if not key:return {}
    path=f"{BASE}/annonces/{urllib.parse.quote(str(source),safe='')}/{urllib.parse.quote(str(reference),safe='')}"
    req=urllib.request.Request(path,headers={'X-Api-Key':key,'Accept':'application/json','User-Agent':'LOGEO/2.1'})
    for attempt in range(2):
        try:
            with urllib.request.urlopen(req,timeout=30) as r: raw=r.read()
            data=json.loads(raw.decode('utf-8'))
            if not isinstance(data,dict):return {}
            for k in ('annonce','listing','item','data','result'):
                if isinstance(data.get(k),dict):return data[k]
            return data
        except urllib.error.HTTPError as exc:
            if exc.code!=429 or attempt:return {}
            retry_after=exc.headers.get('Retry-After')
            try: delay=min(max(float(retry_after),1.1),15.0)
            except Exception: delay=2.0
            time.sleep(delay)
        except Exception:return {}
    return {}

_DESCRIPTION_KEYS=(
    'description','description_full','full_description','description_long',
    'long_description','descriptif','texte','ad_text','listing_description',
    'description_text','description_html'
)

def _clean_description(value):
    if value is None:return ''
    if isinstance(value,dict):
        for k in ('text','html','content','value','description'):
            if isinstance(value.get(k),str) and value.get(k).strip():
                return _clean_description(value[k])
        return ''
    if isinstance(value,list):
        parts=[]
        for x in value:
            p=_clean_description(x)
            if p:parts.append(p)
        return '\n\n'.join(parts).strip()
    v=str(value)
    v=re.sub(r'<br\s*/?>','\n',v,flags=re.I)
    v=re.sub(r'</p\s*>','\n\n',v,flags=re.I)
    v=re.sub(r'<[^>]+>','',v)
    v=html.unescape(v)
    v=re.sub(r'\n{3,}','\n\n',v).strip()
    return v

def _description(d):
    """Extract the complete description from the detail response.

    Explicit description fields are preferred over generic content/body
    fields. This prevents a short search-preview (such as ~502 chars) from
    replacing the actual annonce.description returned by the detail endpoint.
    """
    if not isinstance(d,dict):return ''
    candidates=[]

    # Exact fields on the detail object.
    for key in _DESCRIPTION_KEYS:
        if key in d:
            v=_clean_description(d.get(key))
            if v:candidates.append((v,100))

    # Common nested API wrappers/objects.
    for container_key in ('annonce','listing','item','data','result','details','property'):
        obj=d.get(container_key)
        if isinstance(obj,dict) and obj is not d:
            for key in _DESCRIPTION_KEYS:
                if key in obj:
                    v=_clean_description(obj.get(key))
                    if v:candidates.append((v,100))

    # Fallback only: generic fields are lower priority than explicit
    # description fields.
    def walk(x,depth=0):
        if depth>5:return
        if isinstance(x,dict):
            for k,v in x.items():
                if str(k).lower() in ('content','body','text','value'):
                    cv=_clean_description(v)
                    if cv:candidates.append((cv,20))
                if isinstance(v,(dict,list)):walk(v,depth+1)
        elif isinstance(x,list):
            for v in x:walk(v,depth+1)
    walk(d)

    if not candidates:return ''
    return max(candidates,key=lambda x:(x[1],len(x[0])))[0]

def enrich_listing_full(listing_id):
    u=logeo.require_role('owner')
    if not u:return jsonify(error='Connexion propriétaire requise'),401
    if u is False:return jsonify(error='Compte étudiant'),403
    c=logeo.db();row=c.execute(logeo.ph('SELECT * FROM listings WHERE id=? AND owner_id=?'),(listing_id,u['id'])).fetchone();c.close()
    if not row:return jsonify(error='Annonce introuvable'),404
    source=row['source'] if 'source' in row.keys() else None
    reference=row['source_reference'] if 'source_reference' in row.keys() else None
    if not source or not reference:return jsonify(ok=True,listing=dict(row),enriched=False)

    # ONE detail request only. Do not use the search result/preview and do not
    # call duplicate portals on the Free tier.
    detail=_detail(source,reference)
    if not detail:
        return jsonify(ok=True,listing=dict(row),enriched=False,error_detail='Détail Chercher-Trouver indisponible')

    merged=dict(row)
    merged.update(detail)
    desc=_description(detail)
    current=_clean_description(merged.get('description') or '')
    merged['description']=desc or current

    for k,v in le._derive(merged['description'],merged).items():
        if merged.get(k) in (None,''):merged[k]=v

    updated=le._update(listing_id,merged)
    length=len((updated or {}).get('description') or '')
    print(f'LOGEO: description refresh complete listing={listing_id} source={source}/{reference} description_length={length}')
    return jsonify(ok=True,enriched=True,description_length=length,listing=updated)

logeo.app.view_functions['enrich_listing']=enrich_listing_full
print('LOGEO: full description refresh enabled - single detail endpoint / exact annonce.description / no preview truncation')
