import json, urllib.parse, urllib.request
from flask import jsonify, request
import app as logeo

BASE='https://cherchertrouver.immo/api/v1'

def _photos(item):
    p=item.get('images',item.get('photos',[]))
    if isinstance(p,str):
        try:p=json.loads(p)
        except Exception:p=[]
    return p if isinstance(p,list) else []

def _detail(source, reference):
    """Récupère le détail complet Chercher-Trouver : la recherche est volontairement légère."""
    key=__import__('os').environ.get('CHERCHER_TROUVER_API_KEY','').strip()
    if not key or not source or not reference:return {}
    try:
        path=f"{BASE}/annonces/{urllib.parse.quote(str(source),safe='')}/{urllib.parse.quote(str(reference),safe='')}"
        req=urllib.request.Request(path,headers={'X-Api-Key':key,'Accept':'application/json','User-Agent':'LOGEO/1.0'},method='GET')
        with urllib.request.urlopen(req,timeout=15) as r:
            data=json.loads(r.read().decode('utf-8'))
        return data.get('annonce',data) if isinstance(data,dict) else {}
    except Exception:
        return {}

def _merge_detail(item, source, reference):
    detail=_detail(source,reference)
    if not detail:return item
    merged=dict(item or {})
    # Le détail est prioritaire pour les champs absents ou plus complets.
    for k,v in detail.items():
        if v not in (None,'',[],{}): merged[k]=v
    # Quelques noms rencontrés selon les portails normalisés.
    aliases={
        'floor':['floor','etage','étage'],
        'furnished':['furnished','meuble','meublé'],
        'available_date':['available_date','availability_date','available_from','disponible_le'],
        'description':['description','descriptif','texte'],
        'bedrooms':['bedrooms','chambres'],
        'bathrooms':['bathrooms','salles_de_bains'],
        'rooms':['rooms','pieces','pièces']
    }
    for target,names in aliases.items():
        if merged.get(target) in (None,'',[]):
            for name in names:
                if detail.get(name) not in (None,'',[]):
                    merged[target]=detail[name];break
    return merged

def _payload(item, source, external):
    return {
        'listing_kind':'sale' if item.get('transaction_type') == 'vente' else 'location',
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
        'dpe_class':item.get('dpe'),
        'dpe_value':item.get('dpe_value'),
        'ghg_class':item.get('ges'),
        'ghg_value':item.get('ges_value'),
        'description':item.get('description') or '',
        'photos':_photos(item)[:30],
        'source':source,
        'source_url':external,
        'furnished':item.get('furnished',False),
        'available_date':item.get('available_date')
    }

def _update_existing(c, existing, payload):
    """Enrichit une annonce déjà importée au lieu de simplement répondre duplicate."""
    updates=[]
    values=[]
    for field in ('description','floor','total_floors','furnished','available_date','bedrooms','bathrooms','photos','dpe_class','dpe_value','ghg_class','ghg_value','postal_code','address','neighborhood','heating','heating_type','parking','garage','balcony','terrace','garden','cellar','elevator'):
        value=payload.get(field)
        if value not in (None,'',[],{}):
            if field=='photos':value=json.dumps(value,ensure_ascii=False)
            updates.append(f'{field}=?');values.append(value)
    if not updates:return
    values.append(existing['id'])
    c.execute(logeo.ph('UPDATE listings SET '+','.join(updates)+' WHERE id=?'),values)
    c.commit()

@logeo.app.post('/api/market-import')
def market_import():
    u=logeo.user()
    if not u or u['role']!='owner':return jsonify(error='Connexion propriétaire requise'),403
    x=request.get_json(silent=True) or {}
    source,reference=str(x.get('source') or '').strip(),str(x.get('reference') or '').strip()
    item=x.get('listing') if isinstance(x.get('listing'),dict) else None
    try:
        if not item and source and reference:
            import market_search
            item=market_search.cached_listing(source,reference)
        if not item:return jsonify(error='Annonce non disponible en mémoire. Relance la recherche puis réessaie.'),404
        source=str(item.get('source') or source);reference=str(item.get('reference') or reference)
        # IMPORTANT : /annonces donne une fiche synthétique. On récupère ici la fiche complète
        # afin de conserver le descriptif, l'étage, le meublé, la disponibilité et les caractéristiques.
        item=_merge_detail(item,source,reference)
        external=item.get('external_url')
        if not external:
            for s in (item.get('sources') or []):
                if s.get('source')==source and s.get('url'):external=s['url'];break
            if not external and item.get('sources'):external=item['sources'][0].get('url')
        c=logeo.db()
        try:
            existing=c.execute(logeo.ph('SELECT * FROM listings WHERE source_url=?'),(external,)).fetchone() if external else None
            if existing:
                payload=_payload(item,source,external)
                _update_existing(c,existing,payload)
                row=c.execute(logeo.ph('SELECT * FROM listings WHERE id=?'),(existing['id'],)).fetchone()
                return jsonify(ok=True,duplicate=True,enriched=True,id=existing['id'],listing=dict(row))
        finally:
            c.close()
        import owner_extended
        return owner_extended._insert(_payload(item,source,external),u)
    except Exception as e:return jsonify(error=f'Import ChercherTrouver impossible : {type(e).__name__}: {e}'),500
