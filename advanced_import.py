import os, json
from flask import request, jsonify
import app as logeo

APIFY_TOKEN=os.environ.get('APIFY_API_TOKEN') or os.environ.get('APIFY_API_TOKEN')
APIFY_ACTOR='data_forge_org~apify-seloger'


def _apify(url):
    import urllib.request
    endpoint=f'https://api.apify.com/v2/acts/{APIFY_ACTOR}/run-sync-get-dataset-items?token={APIFY_TOKEN}'
    body=json.dumps({'startUrls':[{'url':url}], 'maxItems':1, 'include_details':True, 'maxImages':50, 'proxyConfiguration':{'useApifyProxy':True,'apifyProxyGroups':['RESIDENTIAL'],'apifyProxyCountry':'FR'}}).encode()
    req=urllib.request.Request(endpoint,data=body,headers={'Content-Type':'application/json','Accept':'application/json'},method='POST')
    with urllib.request.urlopen(req,timeout=90) as r:return json.loads(r.read().decode())

def _normalize(x,url):
    if not x: raise ValueError('SeLoger n’a retourné aucune annonce.')
    p=x.get('prices') if isinstance(x.get('prices'),dict) else {}
    price=x.get('price') or p.get('value') or p.get('amount')
    photos=x.get('photos') or x.get('photos_urls') or x.get('images') or x.get('imageUrls') or []
    if isinstance(photos,str): photos=[u.strip() for u in photos.split('|') if u.strip()]
    out={
      'title':x.get('title') or x.get('titre_annonce') or x.get('headline') or 'Annonce immobilière',
      'city':x.get('city') or x.get('ville') or x.get('address_city') or '',
      'postal_code':x.get('postcode') or x.get('code_postal') or x.get('zipCode') or x.get('postalCode') or '',
      'district':x.get('district') or '', 'address':x.get('address') or '',
      'price':price or 0, 'surface':x.get('surface') or x.get('surface_m2') or x.get('areaSqm') or 0,
      'rooms':x.get('rooms') or x.get('nb_pieces') or x.get('nb_rooms') or 0,
      'bedrooms':x.get('bedrooms') or x.get('nb_chambres') or 0,
      'floor':x.get('floor') or x.get('etage') or '',
      'type':x.get('propertyType') or x.get('type_bien') or x.get('property_type') or 'Appartement',
      'description':x.get('description') or '', 'furnished':bool(x.get('meuble') or x.get('furnished')),
      'dpe':x.get('energyClass') or x.get('dpe_classe') or x.get('dpe') or '',
      'ges':x.get('ges_classe') or x.get('ges') or '',
      'latitude':x.get('latitude'), 'longitude':x.get('longitude'),
      'features':x.get('features') or x.get('amenities') or x.get('amenities_str') or [],
      'photos':photos, 'source_url':x.get('url') or x.get('listingUrl') or url,
      'source':'seloger.com'
    }
    return out

@logeo.app.post('/api/import-preview')
def import_preview():
    try:
        u=logeo.user()
        if not u:return jsonify(error='Connexion requise'),401
        if u['role']!='owner':return jsonify(error='Import réservé aux propriétaires / agences'),403
        url=str((request.get_json(silent=True) or {}).get('url') or '').strip()
        if not url:return jsonify(error='Colle le lien de l’annonce'),400
        if not APIFY_TOKEN:return jsonify(error='APIFY_API_TOKEN est absent de Railway'),500
        data=_apify(url)
        item=data[0] if isinstance(data,list) else data
        return jsonify(ok=True,preview=_normalize(item,url))
    except Exception as e:return jsonify(error=f'Import SeLoger Apify : {e}'),422
