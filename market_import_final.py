import app as logeo
from flask import jsonify, request
import description_refresh as dr

# Final market-import router: existing listings are refreshed directly, so the
# legacy importer cannot make a second Chercher-Trouver detail request first.

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
    if external:
        c=logeo.db()
        try:
            row=c.execute(logeo.ph('SELECT id FROM listings WHERE source_url=? AND owner_id=?'),(external,u['id'])).fetchone()
        finally:c.close()
        if row:
            # One controlled detail request, with 429 retry logic.
            result=dr.enrich_listing_full(row['id'])
            try:
                payload=result.get_json() if hasattr(result,'get_json') else None
                if isinstance(payload,dict):
                    payload['duplicate']=True
                    payload['message']='Annonce déjà présente : enrichissement complet relancé.'
                    return jsonify(payload)
            except Exception: pass
            return result
    # New listing: delegate to the already-tested importer.
    old=logeo.app.view_functions.get('market_import_legacy')
    if old:return old()
    return jsonify(error='Importeur indisponible'),500

# Preserve the currently registered importer before replacing it.
_legacy=logeo.app.view_functions.get('market_import')
if _legacy and 'market_import_legacy' not in logeo.app.view_functions:
    logeo.app.view_functions['market_import_legacy']=_legacy
logeo.app.view_functions['market_import']=_handler
print('LOGEO: final market import router enabled - existing listings refresh directly')
