import json
from flask import jsonify, request
import app as logeo

def _photos(item):
    p=item.get('images',item.get('photos',[]))
    if isinstance(p,str):
        try:p=json.loads(p)
        except Exception:p=[]
    return p if isinstance(p,list) else []

def _payload(item, source, external):
    return {'listing_kind':'sale' if item.get('transaction_type') == 'vente' else 'location','title':item.get('title') or 'Annonce immobilière','city':item.get('city') or '','postal_code':item.get('postal_code'),'address':item.get('address'),'neighborhood':item.get('neighborhood'),'price':item.get('price') or 0,'surface':item.get('surface') or 0,'type':item.get('type') or 'Appartement','rooms':item.get('rooms'),'bedrooms':item.get('bedrooms'),'bathrooms':item.get('bathrooms'),'parking':item.get('parking'),'cellar':item.get('cellar'),'garden':item.get('garden'),'elevator':item.get('elevator'),'balcony':item.get('balcony'),'terrace':item.get('terrace'),'garage':item.get('garage'),'floor':item.get('floor'),'total_floors':item.get('total_floors'),'heating':item.get('heating'),'heating_type':item.get('heating_type'),'air_conditioning':item.get('air_conditioning'),'double_glazing':item.get('double_glazing'),'internet_fiber':item.get('internet_fiber'),'dpe_class':item.get('dpe'),'dpe_value':item.get('dpe_value'),'ghg_class':item.get('ges'),'ghg_value':item.get('ges_value'),'description':item.get('description') or '','photos':_photos(item)[:30],'source':source,'source_url':external,'furnished':item.get('furnished',False),'available_date':item.get('available_date')}

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
        source=str(item.get('source') or source);external=item.get('external_url')
        if not external:
            for s in (item.get('sources') or []):
                if s.get('source')==source and s.get('url'):external=s['url'];break
            if not external and item.get('sources'):external=item['sources'][0].get('url')
        c=logeo.db()
        try:
            existing=c.execute(logeo.ph('SELECT * FROM listings WHERE source_url=?'),(external,)).fetchone() if external else None
            if existing:return jsonify(ok=True,duplicate=True,id=existing['id'],listing=dict(existing))
        finally:c.close()
        import owner_extended
        return owner_extended._insert(_payload(item,source,external),u)
    except Exception as e:return jsonify(error=f'Import ChercherTrouver impossible : {type(e).__name__}: {e}'),500
