import json, os, urllib.parse, urllib.request
from datetime import datetime
from flask import request, jsonify
import app as logeo

_FIELDS={'listing_kind':"TEXT DEFAULT 'location'",'postal_code':'TEXT','address':'TEXT','neighborhood':'TEXT','rooms':'REAL','bedrooms':'REAL','bathrooms':'REAL','floor':'TEXT','total_floors':'TEXT','elevator':'INTEGER DEFAULT 0','parking':'INTEGER DEFAULT 0','garage':'INTEGER DEFAULT 0','balcony':'INTEGER DEFAULT 0','terrace':'INTEGER DEFAULT 0','garden':'INTEGER DEFAULT 0','cellar':'INTEGER DEFAULT 0','heating':'TEXT','heating_type':'TEXT','air_conditioning':'INTEGER DEFAULT 0','double_glazing':'INTEGER DEFAULT 0','internet_fiber':'INTEGER DEFAULT 0','rent_excluding_charges':'REAL','charges':'REAL','deposit':'REAL','lease_type':'TEXT','tenant_fees':'REAL','dpe_class':'TEXT','dpe_value':'REAL','ghg_class':'TEXT','ghg_value':'REAL','photos':"TEXT DEFAULT '[]'"}

def _ensure_schema():
 c=logeo.db()
 for name,spec in _FIELDS.items():
  try:c.execute(f'ALTER TABLE listings ADD COLUMN {name} {spec}')
  except Exception:pass
 c.commit();c.close()
_ensure_schema()
def _bool(v):return 1 if str(v).lower() in ('1','true','yes','oui','on') else 0
def _num(v):
 if v in (None,''):return None
 try:return float(v)
 except:return None
def _photos(x):
 p=x.get('photos',x.get('images',[]))
 if isinstance(p,str):
  try:p=json.loads(p)
  except Exception:p=[]
 return p if isinstance(p,list) else []

def _values(x,u):
 p=_photos(x)[:50]
 v={k:x.get(k) for k in _FIELDS}
 v.update({'listing_kind':x.get('listing_kind') or 'location','postal_code':x.get('postal_code'),'address':x.get('address'),'neighborhood':x.get('neighborhood'),'rooms':_num(x.get('rooms')),'bedrooms':_num(x.get('bedrooms')),'bathrooms':_num(x.get('bathrooms')),'floor':x.get('floor'),'total_floors':x.get('total_floors'),'elevator':_bool(x.get('elevator')),'parking':_bool(x.get('parking')),'garage':_bool(x.get('garage')),'balcony':_bool(x.get('balcony')),'terrace':_bool(x.get('terrace')),'garden':_bool(x.get('garden')),'cellar':_bool(x.get('cellar')),'air_conditioning':_bool(x.get('air_conditioning')),'double_glazing':_bool(x.get('double_glazing')),'internet_fiber':_bool(x.get('internet_fiber')),'rent_excluding_charges':_num(x.get('rent_excluding_charges')),'charges':_num(x.get('charges')),'deposit':_num(x.get('deposit')),'tenant_fees':_num(x.get('tenant_fees')),'dpe_value':_num(x.get('dpe_value')),'ghg_value':_num(x.get('ghg_value')),'photos':json.dumps(p,ensure_ascii=False),'title':x['title'],'city':x['city'],'price':_num(x['price']) or 0,'surface':_num(x['surface']) or 0,'type':x['type'],'distance_km':_num(x.get('distance_km')) or 0,'furnished':_bool(x.get('furnished')),'available_date':x.get('available_date'),'source':x.get('source') or 'owner','source_url':x.get('source_url'),'description':x.get('description') or '','owner_id':u['id'],'created_at':datetime.utcnow().isoformat()})
 return v

def _insert(x,u):
 v=_values(x,u);cols=list(v.keys());vals=[v[c] for c in cols];c=logeo.db();cur=c.execute('INSERT INTO listings('+','.join(cols)+') VALUES('+','.join('?' for _ in cols)+')',vals);c.commit();lid=cur.lastrowid;row=c.execute('SELECT * FROM listings WHERE id=?',(lid,)).fetchone();c.close();return jsonify(ok=True,id=lid,listing=dict(row))

def _ct_api(path,params=None):
 key=os.environ.get('CHERCHER_TROUVER_API_KEY')
 if not key: raise RuntimeError('CHERCHER_TROUVER_API_KEY est absente de Railway')
 url='https://cherchertrouver.immo/api/v1/'+path
 if params:
  url += '?' + urllib.parse.urlencode([(k,v) for k,v in params.items() if v not in (None,'','all') and v is not None],doseq=True)
 req=urllib.request.Request(url,headers={'X-Api-Key':key,'Accept':'application/json','User-Agent':'LOGEO/1.0'},method='GET')
 with urllib.request.urlopen(req,timeout=30) as r:
  return json.loads(r.read().decode('utf-8'))

def _market_item(a):
 return {'source':a.get('source'),'reference':a.get('reference'),'title':a.get('title'),'type':a.get('type'),'transaction_type':a.get('transaction_type') or a.get('transactionType'),'price':a.get('price'),'price_per_m2':a.get('price_per_m2'),'surface':a.get('surface'),'rooms':a.get('rooms'),'bedrooms':a.get('bedrooms'),'bathrooms':a.get('bathrooms'),'city':a.get('city'),'postal_code':a.get('postal_code'),'latitude':a.get('latitude'),'longitude':a.get('longitude'),'dpe':a.get('dpe'),'ges':a.get('ges'),'seller_type':a.get('seller_type'),'seller_name':a.get('seller_name'),'real_estate_network':a.get('real_estate_network'),'exclusive':a.get('exclusive'),'images':a.get('images') or [],'images_count':a.get('images_count') or len(a.get('images') or []),'description':a.get('description'),'external_url':a.get('external_url'),'sources':a.get('sources'),'published_at':a.get('published_at'),'updated_at':a.get('updated_at')}

@logeo.app.get('/api/market-search')
def market_search():
 u=logeo.require_role('owner')
 if not u:return jsonify(error='Connexion propriétaire requise'),401
 if u is False:return jsonify(error='Compte étudiant'),403
 q=request.args
 params={'ville':q.get('ville'),'cp':q.get('cp'),'type':q.get('type'),'transaction':q.get('transaction'),'prix_min':q.get('prix_min'),'prix_max':q.get('prix_max'),'surface_min':q.get('surface_min'),'surface_max':q.get('surface_max'),'pieces_min':q.get('pieces_min'),'chambres_min':q.get('chambres_min'),'dpe':q.get('dpe'),'sort':q.get('sort') or 'recent','page':q.get('page') or 1,'page_size':min(int(q.get('page_size') or 25),100)}
 try:
  data=_ct_api('annonces',params);data['items']=[_market_item(a) for a in data.get('items',[])];return jsonify(data)
 except urllib.error.HTTPError as e:
  try: detail=json.loads(e.read().decode())
  except Exception: detail={}
  return jsonify(error=detail.get('error') or f'API marché HTTP {e.code}',code=detail.get('code')),e.code
 except Exception as e:return jsonify(error=str(e)),500

@logeo.app.get('/api/market-detail/<source>/<reference>')
def market_detail(source,reference):
 u=logeo.require_role('owner')
 if not u:return jsonify(error='Connexion propriétaire requise'),401
 if u is False:return jsonify(error='Compte étudiant'),403
 try:return jsonify(annonce=_market_item(_ct_api(f'annonces/{urllib.parse.quote(source,safe="")}/{urllib.parse.quote(reference,safe="")}').get('annonce',{})))
 except urllib.error.HTTPError as e:return jsonify(error=f'Annonce introuvable ({e.code})'),e.code
 except Exception as e:return jsonify(error=str(e)),500

@logeo.app.post('/api/market-import')
def market_import():
 u=logeo.require_role('owner')
 if not u:return jsonify(error='Connexion propriétaire requise'),401
 if u is False:return jsonify(error='Compte étudiant'),403
 x=request.get_json(silent=True) or {};a=x.get('annonce') or {}
 if not a.get('title') or not a.get('city') or a.get('price') in (None,'') or a.get('surface') in (None,''):return jsonify(error='Annonce incomplète'),400
 d={'listing_kind':'vente' if a.get('transaction_type')=='vente' else 'location','title':a['title'],'type':a.get('type') or 'Appartement','city':a['city'],'postal_code':a.get('postal_code'),'price':a.get('price'),'surface':a.get('surface'),'rooms':a.get('rooms'),'bedrooms':a.get('bedrooms'),'bathrooms':a.get('bathrooms'),'dpe_class':a.get('dpe'),'ghg_class':a.get('ges'),'photos':a.get('images') or [],'description':a.get('description') or '','source':a.get('source') or 'cherchertrouver','source_url':a.get('external_url'),'address':None,'parking':False,'elevator':False,'seller_name':a.get('seller_name'),'real_estate_network':a.get('real_estate_network')}
 return _insert(d,u)

@logeo.app.post('/api/import-preview')
def import_preview_extended():
 u=logeo.require_role('owner')
 if not u:return jsonify(error='Connexion propriétaire requise'),401
 if u is False:return jsonify(error='Compte étudiant'),403
 url=str((request.get_json(silent=True) or {}).get('url') or '').strip()
 if not url:return jsonify(error='Colle le lien de l’annonce'),400
 try:
  import owner_import
  d=owner_import.parse_url(url)
  try:d['photos']=json.loads(d.get('photos') or '[]')
  except Exception:d['photos']=[]
  low=((d.get('title') or '')+' '+(d.get('description') or '')).lower();d.setdefault('listing_kind','location');d.setdefault('lease_type','Meublé' if d.get('furnished') else 'Vide');d.setdefault('rooms',1 if 'studio' in low else None)
  return jsonify(ok=True,preview=d)
 except ValueError as e:return jsonify(error=str(e)),422
 except Exception as e:return jsonify(error=f'Analyse impossible : {type(e).__name__}'),500

@logeo.app.post('/api/owner/create-listing')
def owner_create_extended():
 u=logeo.require_role('owner')
 if not u:return jsonify(error='Connexion propriétaire requise'),401
 if u is False:return jsonify(error='Compte étudiant'),403
 x=request.get_json(silent=True) or {}
 if any(x.get(k) in (None,'') for k in ('title','city','price','surface','type')):return jsonify(error='Titre, ville, prix, surface et type sont requis'),400
 return _insert(x,u)

@logeo.app.post('/api/owner/import-to-listing')
def owner_import_to_listing():
 u=logeo.require_role('owner')
 if not u:return jsonify(error='Connexion propriétaire requise'),401
 if u is False:return jsonify(error='Compte étudiant'),403
 x=request.get_json(silent=True) or {}
 if not x.get('title') or not x.get('city') or x.get('price') in (None,'') or x.get('surface') in (None,''):return jsonify(error='L’import doit fournir au minimum titre, ville, prix et surface'),400
 return _insert(x,u)

@logeo.app.after_request
def owner_extended_ui(response):
 try:
  if response.content_type and response.content_type.startswith('text/html'):
   page=response.get_data(as_text=True)
   if 'id="ownerApp"' in page and 'ownerExtendedForm' not in page:
    response.set_data(page.replace('</body>','<script src="/static/owner-extended.js?v=3"></script><script src="/static/market-import.js?v=1"></script></body>'))
 except Exception:pass
 return response
