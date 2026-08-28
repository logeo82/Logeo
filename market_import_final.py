import app as logeo
from flask import jsonify, request
import description_refresh as dr

def _external(item):
    u=item.get('external_url') if isinstance(item,dict) else None
    if u:return str(u)
    for s in (item.get('sources') or []) if isinstance(item,dict) else []:
        if isinstance(s,dict) and s.get('url'): return str(s['url'])
    return ''

def _handler():
    u=logeo.user()
    if not u or u.get('role')!='owner': return jsonify(error='Connexion propriétaire requise'),403
    x=request.get_json(silent=True) or {}
    item=x.get('listing') if isinstance(x.get('listing'),dict) else {}
    source=str(item.get('source') or x.get('source') or '').strip()
    reference=str(item.get('reference') or x.get('reference') or '').strip()
    external=_external(item)
    c=logeo.db()
    try:
        row=None
        if external:
            row=c.execute(logeo.ph('SELECT id FROM listings WHERE source_url=? AND owner_id=?'),(external,u['id'])).fetchone()
        if not row and source and reference:
            row=c.execute(logeo.ph('SELECT id FROM listings WHERE source=? AND source_reference=? AND owner_id=?'),(source,reference,u['id'])).fetchone()
    finally:c.close()
    if row:
        result=dr.enrich_listing_full(row['id'])
        try:
            payload=result.get_json() if hasattr(result,'get_json') else None
            if isinstance(payload,dict):
                payload['duplicate']=True
                if payload.get('enriched'):
                    payload['message']='Annonce déjà présente : descriptif réenrichi.'
                else:
                    payload['message']='Annonce déjà présente : enrichissement indisponible pour le moment.'
                return jsonify(payload)
        except Exception: pass
        return result
    old=logeo.app.view_functions.get('market_import_legacy')
    if old:return old()
    return jsonify(error='Importeur indisponible'),500

_legacy=logeo.app.view_functions.get('market_import')
if _legacy and 'market_import_legacy' not in logeo.app.view_functions:
    logeo.app.view_functions['market_import_legacy']=_legacy
logeo.app.view_functions['market_import']=_handler
print('LOGEO: final market import router enabled - existing listings refresh directly')
