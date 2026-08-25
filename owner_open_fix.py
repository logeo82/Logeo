from flask import jsonify
import app as logeo

@logeo.app.get('/api/owner/listing/<int:lid>')
def owner_listing_detail(lid):
    u = logeo.require_role('owner')
    if not u:
        return jsonify(error='Connexion propriétaire requise'), 401
    if u is False:
        return jsonify(error='Compte étudiant'), 403
    c = logeo.db()
    try:
        row = c.execute('SELECT * FROM listings WHERE id=? AND owner_id=?', (lid, u['id'])).fetchone()
        if not row:
            return jsonify(error='Annonce introuvable'), 404
        return jsonify(listing=dict(row))
    finally:
        c.close()
