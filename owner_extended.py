import json, os, base64
from datetime import datetime
from flask import request, jsonify
import app as logeo

# Extended listing fields inspired by SeLoger's public listing guidance.
_FIELDS = {
    'listing_kind': "TEXT DEFAULT 'location'",
    'postal_code': 'TEXT',
    'address': 'TEXT',
    'neighborhood': 'TEXT',
    'rooms': 'REAL',
    'bedrooms': 'REAL',
    'bathrooms': 'REAL',
    'floor': 'TEXT',
    'total_floors': 'TEXT',
    'elevator': 'INTEGER DEFAULT 0',
    'parking': 'INTEGER DEFAULT 0',
    'garage': 'INTEGER DEFAULT 0',
    'balcony': 'INTEGER DEFAULT 0',
    'terrace': 'INTEGER DEFAULT 0',
    'garden': 'INTEGER DEFAULT 0',
    'cellar': 'INTEGER DEFAULT 0',
    'heating': 'TEXT',
    'heating_type': 'TEXT',
    'air_conditioning': 'INTEGER DEFAULT 0',
    'double_glazing': 'INTEGER DEFAULT 0',
    'internet_fiber': 'INTEGER DEFAULT 0',
    'rent_excluding_charges': 'REAL',
    'charges': 'REAL',
    'deposit': 'REAL',
    'lease_type': 'TEXT',
    'tenant_fees': 'REAL',
    'dpe_class': 'TEXT',
    'dpe_value': 'REAL',
    'ghg_class': 'TEXT',
    'ghg_value': 'REAL',
    'photos': "TEXT DEFAULT '[]'",
}

def _ensure_schema():
    c = logeo.db()
    for name, spec in _FIELDS.items():
        try:
            c.execute(f'ALTER TABLE listings ADD COLUMN {name} {spec}')
        except Exception:
            pass
    c.commit(); c.close()

_ensure_schema()

def _bool(v):
    return 1 if str(v).lower() in ('1','true','yes','oui','on') else 0

def _num(v):
    if v in (None, ''): return None
    try: return float(v)
    except Exception: return None

def _photos(x):
    p=x.get('photos', [])
    if isinstance(p,str):
        try:p=json.loads(p)
        except Exception:p=[]
    return p if isinstance(p,list) else []

@logeo.app.post('/api/owner/create-listing')
def owner_create_extended():
    u=logeo.require_role('owner')
    if not u:return jsonify(error='Connexion propriétaire requise'),401
    if u is False:return jsonify(error='Compte étudiant'),403
    x=request.get_json(silent=True) or {}
    required=['title','city','price','surface','type']
    if any(x.get(k) in (None,'') for k in required):
        return jsonify(error='Titre, ville, prix, surface et type sont requis'),400
    photos=_photos(x)[:30]
    values={k:x.get(k) for k in _FIELDS}
    values.update({
        'listing_kind':x.get('listing_kind') or 'location',
        'postal_code':x.get('postal_code'), 'address':x.get('address'), 'neighborhood':x.get('neighborhood'),
        'rooms':_num(x.get('rooms')), 'bedrooms':_num(x.get('bedrooms')), 'bathrooms':_num(x.get('bathrooms')),
        'floor':x.get('floor'), 'total_floors':x.get('total_floors'),
        'elevator':_bool(x.get('elevator')), 'parking':_bool(x.get('parking')), 'garage':_bool(x.get('garage')),
        'balcony':_bool(x.get('balcony')), 'terrace':_bool(x.get('terrace')), 'garden':_bool(x.get('garden')), 'cellar':_bool(x.get('cellar')),
        'air_conditioning':_bool(x.get('air_conditioning')), 'double_glazing':_bool(x.get('double_glazing')), 'internet_fiber':_bool(x.get('internet_fiber')),
        'rent_excluding_charges':_num(x.get('rent_excluding_charges')), 'charges':_num(x.get('charges')), 'deposit':_num(x.get('deposit')), 'tenant_fees':_num(x.get('tenant_fees')),
        'dpe_value':_num(x.get('dpe_value')), 'ghg_value':_num(x.get('ghg_value')), 'photos':json.dumps(photos,ensure_ascii=False),
    })
    # Keep the original columns used by the matching engine populated.
    values.update({'title':x['title'],'city':x['city'],'price':_num(x['price']) or 0,'surface':_num(x['surface']) or 0,'type':x['type'],
                   'distance_km':_num(x.get('distance_km')) or 0,'furnished':_bool(x.get('furnished')),'available_date':x.get('available_date'),
                   'source':x.get('source') or 'owner','source_url':x.get('source_url'),'description':x.get('description') or '', 'owner_id':u['id'],
                   'created_at':datetime.utcnow().isoformat()})
    cols=list(values.keys()); vals=[values[c] for c in cols]
    c=logeo.db()
    cur=c.execute('INSERT INTO listings('+','.join(cols)+') VALUES('+','.join('?' for _ in cols)+')',vals)
    c.commit(); lid=cur.lastrowid
    row=c.execute('SELECT * FROM listings WHERE id=?',(lid,)).fetchone();c.close()
    return jsonify(ok=True,id=lid,listing=dict(row))

@logeo.app.post('/api/owner/import-to-listing')
def owner_import_to_listing():
    u=logeo.require_role('owner')
    if not u:return jsonify(error='Connexion propriétaire requise'),401
    if u is False:return jsonify(error='Compte étudiant'),403
    x=request.get_json(silent=True) or {}
    # This endpoint accepts the exact normalized payload returned by an importer.
    if not x.get('title') or not x.get('city') or x.get('price') in (None,'') or x.get('surface') in (None,''):
        return jsonify(error='L’import doit fournir au minimum titre, ville, prix et surface'),400
    x=dict(x); x['owner_id']=u['id']; x['source']=x.get('source') or 'import'; x['photos']=_photos(x)
    # Reuse the same creation contract, so imported and manual listings are identical.
    with logeo.app.test_request_context('/api/owner/create-listing',method='POST',json=x):
        return owner_create_extended()

# Serve a stable owner creation form. It deliberately replaces the minimal legacy form visually,
# while keeping the existing student interface and simulation engine untouched.
@logeo.app.after_request
def owner_extended_ui(response):
    try:
        if response.content_type and response.content_type.startswith('text/html'):
            page=response.get_data(as_text=True)
            if 'id="ownerApp"' in page and 'ownerExtendedForm' not in page:
                script='<script src="/static/owner-extended.js?v=1"></script>'
                page=page.replace('</body>',script+'</body>')
                response.set_data(page)
    except Exception:
        pass
    return response
