import app as logeo
from flask import request, jsonify

@logeo.app.get('/api/owner/listings/<int:lid>')
def owner_listing_detail(lid):
    u=logeo.require_role('owner')
    if not u:return jsonify(error='Connexion propriétaire requise'),401
    if u is False:return jsonify(error='Compte étudiant'),403
    c=logeo.db(); row=c.execute(logeo.ph('SELECT * FROM listings WHERE id=? AND owner_id=?'),(lid,u['id'])).fetchone(); c.close()
    if not row:return jsonify(error='Annonce introuvable'),404
    return jsonify(listing=dict(row))

@logeo.app.patch('/api/owner/listings/<int:lid>')
def owner_listing_update(lid):
    u=logeo.require_role('owner')
    if not u:return jsonify(error='Connexion propriétaire requise'),401
    if u is False:return jsonify(error='Compte étudiant'),403
    x=request.get_json(silent=True) or {}
    allowed=['title','city','price','surface','type','rooms','description']
    vals=[];sets=[]
    for k in allowed:
        if k in x:
            sets.append(k+'=?')
            if k in ('price','surface','rooms'):
                try: vals.append(float(x[k]) if x[k] not in ('',None) else None)
                except: return jsonify(error=f'Valeur invalide pour {k}'),400
            else: vals.append(x[k])
    if not sets:return jsonify(error='Aucune modification'),400
    c=logeo.db();vals += [lid,u['id']]; cur=c.execute(logeo.ph('UPDATE listings SET '+','.join(sets)+' WHERE id=? AND owner_id=?'),vals)
    if cur.rowcount==0:c.close();return jsonify(error='Annonce introuvable'),404
    c.commit();c.close();return jsonify(ok=True)

@logeo.app.delete('/api/owner/listings/<int:lid>')
def owner_listing_delete(lid):
    u=logeo.require_role('owner')
    if not u:return jsonify(error='Connexion propriétaire requise'),401
    if u is False:return jsonify(error='Compte étudiant'),403
    c=logeo.db();cur=c.execute(logeo.ph('DELETE FROM listings WHERE id=? AND owner_id=?'),(lid,u['id']))
    if cur.rowcount==0:c.close();return jsonify(error='Annonce introuvable'),404
    c.commit();c.close();return jsonify(ok=True)

@logeo.app.after_request
def owner_dashboard_ui(response):
    try:
        if not (response.content_type or '').startswith('text/html'): return response
        page=response.get_data(as_text=True)
        if 'id="ownerApp"' not in page or 'ownerDashboardUi' in page:return response
        script='<script id="ownerDashboardUi" src="/static/owner-dashboard.js?v=1"></script>'
        response.set_data(page.replace('</body>',script+'</body>'))
        response.headers['Cache-Control']='no-store, no-cache, must-revalidate, max-age=0'
    except Exception: pass
    return response