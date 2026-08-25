from flask import jsonify
import app as logeo

@logeo.app.get('/api/listing/<int:lid>')
def listing_detail(lid):
    u = logeo.user()
    if not u:
        return jsonify(error='Connexion requise'), 401
    c = logeo.db()
    row = c.execute('SELECT * FROM listings WHERE id=?', (lid,)).fetchone()
    c.close()
    if not row:
        return jsonify(error='Annonce introuvable'), 404
    if u['role'] == 'owner' and row['owner_id'] not in (None, u['id']):
        return jsonify(error='Accès refusé'), 403
    return jsonify(listing=dict(row))
