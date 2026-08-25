from flask import request, jsonify
import app as logeo
from owner_import import parse_url

@logeo.app.post('/api/import-preview')
def import_preview():
    try:
        u = logeo.user()
        if not u:
            return jsonify(error='Connexion requise'), 401
        if u['role'] != 'owner':
            return jsonify(error='Import réservé aux propriétaires / agences'), 403
        payload = request.get_json(silent=True) or {}
        url = str(payload.get('url') or '').strip()
        if not url:
            return jsonify(error='Colle le lien de l’annonce'), 400
        data = parse_url(url)
        return jsonify(ok=True, preview=data)
    except ValueError as e:
        return jsonify(error=str(e)), 422
    except Exception as e:
        return jsonify(error=f'Erreur pendant l’analyse : {type(e).__name__}'), 500
