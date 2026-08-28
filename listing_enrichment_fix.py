import os,json,urllib.parse,urllib.request
from flask import jsonify
import app as logeo
BASE='https://cherchertrouver.immo/api/v1'
def first(d,*keys):
    for k in keys:
        v=d.get(k) if isinstance(d,dict) else None
        if v not in (None,'',[],{}): return v
    return None
def detail_api(source,reference):
    key=os.environ.get('CHERCHER_TROUVER_API_KEY','').strip()
    if not key: raise RuntimeError('CHERCHER_TROUVER_API_KEY absente')
    url=f'{BASE}/annonces/{urllib.parse.quote(str(source),safe="")}/{urllib.parse.quote(str(reference),safe="")}'
    errors=[]
    for h in ({'X-Api-Key':key,'Accept':'application/json','User-Agent':'LOGEO/2.0'},{'Authorization':'Bearer '+key,'Accept':'application/json','User-Agent':'LOGEO/2.0'}):
        try:
            with urllib.request.urlopen(urllib.request.Request(url,headers=h),timeout=25) as r: raw=json.loads(r.read().decode())
            if isinstance(raw,dict):
                for k in ('annonce','listing','item','data'):
                    if isinstance(raw.get(k),dict): return raw[k]
                return raw
        except Exception as e: errors.append(str(e))
    raise RuntimeError('API détail inaccessible: '+' | '.join(errors))
def full_description(a):
    v=first(a,'description','descriptif','texte','ad_text','listing_description','description_text','full_description','body','content')
    if isinstance(v,dict): v=first(v,'text','html','content','value')
    if isinstance(v,list): v='\n\n'.join(str(first(x,'text','html','content') if isinstance(x,dict) else x) for x in v if x not in (None,''))
    if v:return str(v)
    for k in ('details','characteristics','property','features'):
        if isinstance(a.get(k),dict):
            v=full_description(a[k])
            if v:return v
    return ''
def photos(a):
    p=first(a,'images','photos','pictures')
    if isinstance(p,str):
        try:p=json.loads(p)
        except Exception:p=[]
    out=[]
    for x in p if isinstance(p,list) else []:
        x=first(x,'url','src','image','large','original') if isinstance(x,dict) else x
        if x:out.append(str(x))
    return out[:50]
def val(a,*keys):
    v=first(a,*keys)
    if v not in (None,'',[],{}):return v
    for k in ('property','details','characteristics','features'):
        if isinstance(a.get(k),dict):
            v=first(a[k],*keys)
            if v not in (None,'',[],{}):return v
    return None
def save(row_id,a):
    mapping={'source_reference':('reference',),'description':(),'photos':(),'postal_code':('postal_code','cp'),'address':('address','adresse'),'neighborhood':('neighborhood','quartier'),'bedrooms':('bedrooms','chambres'),'bathrooms':('bathrooms','salles_de_bains','sdb'),'rooms':('rooms','pieces','pièces'),'floor':('floor','etage','étage','floor_label'),'total_floors':('total_floors','nombre_etages'),'dpe_class':('dpe_class','dpe','energy_class'),'dpe_value':('dpe_value',),'ghg_class':('ghg_class','ges','ghg_class'),'ghg_value':('ghg_value','ges_value'),'tenant_fees':('tenant_fees','honoraires_locataire'),'charges':('charges','provision_charges'),'deposit':('deposit','depot_garantie'),'heating':('heating',),'heating_type':('heating_type',),'parking':('parking','stationnement'),'garage':('garage',),'balcony':('balcony','balcon'),'terrace':('terrace','terrasse'),'garden':('garden','jardin'),'cellar':('cellar','cave'),'elevator':('elevator','ascenseur'),'latitude':('latitude',),'longitude':('longitude',),'price_per_m2':('price_per_m2',),'land_surface':('land_surface',),'living_room_surface':('living_room_surface',),'year_built':('year_built',),'pool':('pool',),'exclusive':('exclusive',),'legal_info':('legal_info',),'dpe_chart_url':('dpe_chart_url',),'ges_chart_url':('ges_chart_url',),'virtual_tour_url':('virtual_tour_url',),'video_url':('video_url',),'published_at':('published_at',),'seller_type':('seller_type',),'seller_name':('seller_name',),'real_estate_network':('real_estate_network',),'region':('region',),'department':('department',)}
    values={}
    for k,names in mapping.items():
        v=full_description(a) if k=='description' else photos(a) if k=='photos' else val(a,*names)
        if v not in (None,'',[],{}):values[k]=json.dumps(v,ensure_ascii=False) if k=='photos' else v
    c=logeo.db();sets=[];args=[]
    for k,v in values.items():sets.append(f'{k}={"%s" if logeo.USE_PG else "?"}');args.append(v)
    if sets:
        args.append(row_id);c.execute('UPDATE listings SET '+','.join(sets)+(' WHERE id=%s' if logeo.USE_PG else ' WHERE id=?'),args);c.commit()
    r=c.execute(logeo.ph('SELECT * FROM listings WHERE id=?'),(row_id,)).fetchone();c.close();return dict(r) if r else None
def enrich_listing_fix(listing_id):
    u=logeo.require_role('owner')
    if not u:return jsonify(error='Connexion propriétaire requise'),401
    if u is False:return jsonify(error='Compte étudiant'),403
    c=logeo.db();row=c.execute(logeo.ph('SELECT * FROM listings WHERE id=? AND owner_id=?'),(listing_id,u['id'])).fetchone();c.close()
    if not row:return jsonify(error='Annonce introuvable'),404
    source=row['source'] if 'source' in row.keys() else None;reference=row['source_reference'] if 'source_reference' in row.keys() else None
    if not source or not reference:return jsonify(ok=False,error='Source ou référence manquante',listing=dict(row)),422
    try:
        saved=save(listing_id,detail_api(source,reference))
        return jsonify(ok=True,enriched=True,description_length=len(saved.get('description') or ''),listing=saved)
    except Exception as e:return jsonify(ok=False,enriched=False,error=str(e),listing=dict(row)),502
for rule in logeo.app.url_map.iter_rules():
    if rule.rule=='/api/owner/enrich-listing/<int:listing_id>':
        logeo.app.view_functions[rule.endpoint]=enrich_listing_fix
        break
@logeo.app.after_request
def no_cache_owner_detail(response):
    if response.content_type and response.content_type.startswith('text/html'):
        response.headers['Cache-Control']='no-store, no-cache, must-revalidate, max-age=0';response.headers['Pragma']='no-cache'
    return response
