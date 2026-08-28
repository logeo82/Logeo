import json, os, urllib.parse, urllib.request
from flask import jsonify, request
import app as logeo

BASE='https://cherchertrouver.immo/api/v1'

def _photos(item):
    p=item.get('images',item.get('photos',item.get('pictures',[])))
    if isinstance(p,str):
        try:p=json.loads(p)
        except Exception:p=[]
    return p if isinstance(p,list) else []

def _detail(source, reference):
    """Récupère la fiche détaillée CT, avec les deux modes d'authentification documentés."""
    key=os.environ.get('CHERCHER_TROUVER_API_KEY','').strip()
    if not key or not source or not reference:return {}
    path=f"{BASE}/annonces/{urllib.parse.quote(str(source).strip(),safe='')}/{urllib.parse.quote(str(reference).strip(),safe='')}"
    headers={'X-Api-Key':key,'Accept':'application/json','User-Agent':'LOGEO/1.1'}
    for auth_header in ('X-Api-Key','Authorization'):
        try:
            h=dict(headers)
            if auth_header=='Authorization':
                h.pop('X-Api-Key',None);h['Authorization']='Bearer '+key
            req=urllib.request.Request(path,headers=h,method='GET')
            with urllib.request.urlopen(req,timeout=20) as r:
                raw=json.loads(r.read().decode('utf-8'))
            if isinstance(raw,dict):
                for k in ('annonce','item','data','listing'):
                    if isinstance(raw.get(k),dict): return raw[k]
                return raw
        except Exception:
            continue
    return {}

def _first(d,*names):
    if not isinstance(d,dict):return None
    for n in names:
        v=d.get(n)
        if v not in (None,'',[],{}):return v
    return None

def _merge_detail(item, source, reference):
    detail=_detail(source,reference)
    if not detail:return item
    merged=dict(item or {})
    # Le détail est prioritaire pour toutes les valeurs réellement fournies.
    for k,v in detail.items():
        if v not in (None,'',[],{}): merged[k]=v
    aliases={
        'floor':['floor','etage','étage','floor_number','floor_label'],
        'total_floors':['total_floors','nombre_etages','number_of_floors'],
        'furnished':['furnished','meuble','meublé','is_furnished'],
        'available_date':['available_date','availability_date','available_from','available_at','disponible_le','date_disponibilite'],
        'description':['description','descriptif','texte','ad_text','listing_description','description_text'],
        'bedrooms':['bedrooms','chambres','bedroom_count','nb_chambres'],
        'bathrooms':['bathrooms','salles_de_bains','sdb','bathroom_count','nb_sdb'],
        'rooms':['rooms','pieces','pièces','room_count'],
        'dpe':['dpe','dpe_class','energy_class'],
        'ges':['ges','ghg_class','greenhouse_class'],
        'heating':['heating','chauffage','heating_system'],
        'heating_type':['heating_type','type_chauffage'],
        'parking':['parking','stationnement'],
        'garage':['garage'],
        'terrace':['terrace','terrasse'],
        'balcony':['balcony','balcon'],
        'garden':['garden','jardin'],
        'cellar':['cellar','cave'],
        'elevator':['elevator','ascenseur'],
        'address':['address','adresse'],
        'neighborhood':['neighborhood','quartier']
    }
    for target,names in aliases.items():
        v=_first(detail,*names)
        if v not in (None,'',[],{}): merged[target]=v
    # Certains champs détaillés peuvent être regroupés dans un objet characteristics/features.
    for container_name in ('characteristics','features','details','property'):
        sub=detail.get(container_name)
        if isinstance(sub,dict):
            for target,names in aliases.items():
                if merged.get(target) in (None,'',[]):
                    v=_first(sub,*names)
                    if v not in (None,'',[],{}):merged[target]=v
    return merged

def _payload(item, source, external):
    return {
        'listing_kind':'sale' if str(item.get('transaction_type','')).lower() in ('vente','sale','sell') else 'location',
        'title':item.get('title') or 'Annonce immobilière',
        'city':item.get('city') or '',
        'postal_code':item.get('postal_code'),
        'address':item.get('address'),
        'neighborhood':item.get('neighborhood'),
        'price':item.get('price') or 0,
        'surface':item.get('surface') or 0,
        'type':item.get('type') or 'Appartement',
        'rooms':item.get('rooms'),
        'bedrooms':item.get('bedrooms'),
        'bathrooms':item.get('bathrooms'),
        'parking':item.get('parking'),
        'cellar':item.get('cellar'),
        'garden':item.get('garden'),
        'elevator':item.get('elevator'),
        'balcony':item.get('balcony'),
        'terrace':item.get('terrace'),
        'garage':item.get('garage'),
        'floor':item.get('floor'),
        'total_floors':item.get('total_floors'),
        'heating':item.get('heating'),
        'heating_type':item.get('heating_type'),
        'air_conditioning':item.get('air_conditioning'),
        'double_glazing':item.get('double_glazing'),
        'internet_fiber':item.get('internet_fiber'),
        'dpe_class':item.get('dpe_class') or item.get('dpe'),
        'dpe_value':item.get('dpe_value'),
        'ghg_class':item.get('ghg_class') or item.get('ges'),
        'ghg_value':item.get('ges_value'),
        'description':item.get('description') or item.get('descriptif') or item.get('texte') or '',
        'photos':_photos(item)[:30],
        'source':source,
        'source_url':external,
        'furnished':item.get('furnished',False),
        'available_date':item.get('available_date')
    }

def _update_existing(c, existing, payload):
    updates=[];values=[]
    for field in ('description','floor','total_floors','furnished','available_date','bedrooms','bathrooms','photos','dpe_class','dpe_value','ghg_class','ghg_value','postal_code','address','neighborhood','heating','heating_type','parking','garage','balcony','terrace','garden','cellar','elevator'):
        value=payload.get(field)
        if value not in (None,'',[],{}):
            if field=='photos':value=json.dumps(value,ensure_ascii=False)
            updates.append(f'{field}=?');values.append(value)
    if not updates:return
    values.append(existing['id'])
    c.execute(logeo.ph('UPDATE listings SET '+','.join(updates)+' WHERE id=?'),values);c.commit()

@logeo.app.post('/api/market-import')
def market_import():
    u=logeo.user()
    if not u or u['role']!='owner':return jsonify(error='Connexion propriétaire requise'),403
    x=request.get_json(silent=True) or {};source=str(x.get('source') or '').strip();reference=str(x.get('reference') or '').strip();item=x.get('listing') if isinstance(x.get('listing'),dict) else None
    try:
        if not item and source and reference:
            import market_search;item=market_search.cached_listing(source,reference)
        if not item:return jsonify(error='Annonce non disponible en mémoire. Relance la recherche puis réessaie.'),404
        source=str(item.get('source') or source);reference=str(item.get('reference') or reference)
        item=_merge_detail(item,source,reference)
        external=item.get('external_url')
        if not external:
            for s in (item.get('sources') or []):
                if isinstance(s,dict) and s.get('url') and (not source or s.get('source')==source):external=s['url'];break
        if not external and item.get('sources') and isinstance(item['sources'][0],dict):external=item['sources'][0].get('url')
        c=logeo.db()
        try:
            existing=c.execute(logeo.ph('SELECT * FROM listings WHERE source_url=?'),(external,)).fetchone() if external else None
            if existing:
                payload=_payload(item,source,external);_update_existing(c,existing,payload);row=c.execute(logeo.ph('SELECT * FROM listings WHERE id=?'),(existing['id'],)).fetchone();return jsonify(ok=True,duplicate=True,enriched=True,id=existing['id'],listing=dict(row))
        finally:c.close()
        import owner_extended
        return owner_extended._insert(_payload(item,source,external),u)
    except Exception as e:return jsonify(error=f'Import ChercherTrouver impossible : {type(e).__name__}: {e}'),500
