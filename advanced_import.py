import os, json
from flask import request, jsonify
import app as logeo

APIFY_TOKEN = os.environ.get('APIFY_API_TOKEN')
APIFY_ACTOR = os.environ.get('SELOGER_APIFY_ACTOR', 'memo23~seloger-scraper')


def _apify(url):
    import urllib.request
    endpoint = f'https://api.apify.com/v2/acts/{APIFY_ACTOR}/run-sync-get-dataset-items?token={APIFY_TOKEN}'
    payload = {'startUrls': [url], 'maxItems': 1, 'enrichAgency': False, 'maxRequestRetries': 5,
               'useInternalHandler': True,
               'proxy': {'useApifyProxy': True, 'apifyProxyGroups': ['RESIDENTIAL'], 'apifyProxyCountry': 'FR'}}
    req = urllib.request.Request(endpoint, data=json.dumps(payload).encode(),
        headers={'Content-Type': 'application/json', 'Accept': 'application/json'}, method='POST')
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read().decode())


def _first(x, *keys, default=''):
    for k in keys:
        v = x.get(k)
        if v not in (None, '', [], {}): return v
    return default


def _photos(x):
    values=[]
    for key in ('images','photos','imageUrls','photos_urls','image_urls','gallery'):
        v=x.get(key)
        if isinstance(v,list): values.extend(v)
        elif isinstance(v,str): values.extend(v.replace(',', '|').split('|'))
    out=[]; seen=set()
    for item in values:
        if isinstance(item,dict): item=item.get('url') or item.get('imageUrl') or item.get('src')
        if item:
            item=str(item).strip()
            if item and item not in seen: seen.add(item); out.append(item)
    return out


def _normalize(x, url):
    if not x: raise ValueError('Le scraper SeLoger n’a retourné aucune annonce.')
    return {
      'title': _first(x,'title','headline','titre_annonce',default='Annonce immobilière'),
      'city': _first(x,'city','ville','addressCity','address_city'),
      'postal_code': _first(x,'postalCode','postcode','postal_code','zipCode','code_postal'),
      'district': _first(x,'neighborhood','district','quartier'), 'address': _first(x,'address','street','streetAddress'),
      'price': _first(x,'price','prix','rent','salePrice',default=0),
      'surface': _first(x,'surfaceM2','surface','surface_m2','areaSqm',default=0),
      'rooms': _first(x,'rooms','nb_pieces','nb_rooms',default=0), 'bedrooms': _first(x,'bedrooms','nb_chambres',default=0),
      'floor': _first(x,'floor','etage'), 'type': _first(x,'propertyType','property_type','type_bien',default='Appartement'),
      'description': _first(x,'description','descriptionText'), 'furnished': bool(_first(x,'furnished','meuble',default=False)),
      'dpe': _first(x,'dpeClass','energyClass','dpe_classe','dpe'), 'ges': _first(x,'gesClass','ges_classe','ges'),
      'heating': _first(x,'heatingType','heating_type'), 'features': _first(x,'features','amenities','amenities_str',default=[]),
      'latitude': _first(x,'latitude','lat',default=None), 'longitude': _first(x,'longitude','lng','lon',default=None),
      'agency': _first(x,'agencyName','agency_name'), 'transaction_type': _first(x,'transactionType','transaction_type'),
      'price_per_m2': _first(x,'pricePerM2','price_per_m2',default=None), 'photos': _photos(x),
      'source_url': _first(x,'listingUrl','url',default=url), 'source':'seloger.com'
    }


@logeo.app.post('/api/import-preview')
def import_preview():
    try:
        u=logeo.user()
        if not u:return jsonify(error='Connexion requise'),401
        if u['role']!='owner':return jsonify(error='Import réservé aux propriétaires / agences'),403
        url=str((request.get_json(silent=True) or {}).get('url') or '').strip()
        if not url:return jsonify(error='Colle le lien de l’annonce'),400
        if not APIFY_TOKEN:return jsonify(error='APIFY_API_TOKEN est absent de Railway'),500
        data=_apify(url); item=data[0] if isinstance(data,list) else data
        return jsonify(ok=True,preview=_normalize(item,url))
    except Exception as e:return jsonify(error=f'Import SeLoger : {e}'),422
