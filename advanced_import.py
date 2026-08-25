import os, json, re, urllib.request
from flask import request, jsonify, send_from_directory
import app as logeo
from ai_listing_normalizer import normalize_listing
from owner_import import parse_url

APIFY_TOKEN=os.environ.get('APIFY_API_TOKEN')
APIFY_ACTOR='memo23~seloger-scraper'

def _apify(url):
 import urllib.request
 endpoint=f'https://api.apify.com/v2/acts/{APIFY_ACTOR}/run-sync-get-dataset-items?token={APIFY_TOKEN}'
 payload={'startUrls':[url],'maxItems':1,'enrichAgency':True,'maxRequestRetries':5,'proxy':{'useApifyProxy':True,'apifyProxyGroups':['RESIDENTIAL'],'apifyProxyCountry':'FR'}}
 req=urllib.request.Request(endpoint,data=json.dumps(payload).encode(),headers={'Content-Type':'application/json','Accept':'application/json'},method='POST')
 with urllib.request.urlopen(req,timeout=120) as r: raw=json.loads(r.read().decode())
 if isinstance(raw,list):
  if not raw: raise ValueError('Aucune annonce retournée par SeLoger.')
  return raw[0]
 if isinstance(raw,dict):
  if raw.get('errorMessage'): raise ValueError(raw['errorMessage'])
  return raw
 raise ValueError('Réponse Apify invalide.')

def _first(x,*keys,default=''):
 for k in keys:
  v=x.get(k)
  if v not in (None,'',[],{}): return v
 return default

def _photos(x):
 values=[]
 for key in ('imageUrls','images','photos','image_urls','photos_urls','gallery'):
  v=x.get(key)
  if isinstance(v,list): values.extend(v)
  elif isinstance(v,str): values.extend(v.replace(',','|').split('|'))
 out=[];seen=set()
 for item in values:
  if isinstance(item,dict): item=item.get('url') or item.get('imageUrl') or item.get('src')
  if item:
   item=str(item).strip()
   if item and item not in seen: seen.add(item);out.append(item)
 return out

def _normalize(x,url):
 return {'title':_first(x,'title','headline','titre_annonce',default='Annonce immobilière'),'city':_first(x,'city','ville','addressCity','address_city'),'postal_code':_first(x,'postalCode','postcode','postal_code','zipCode','code_postal'),'district':_first(x,'neighborhood','district','quartier'),'address':_first(x,'address','street','streetAddress'),'price':_first(x,'price','prix','rent','salePrice',default=0),'surface':_first(x,'livingArea','surfaceM2','surface','surface_m2','areaSqm',default=0),'rooms':_first(x,'rooms','nb_pieces','nb_rooms',default=0),'bedrooms':_first(x,'bedrooms','nb_chambres',default=0),'floor':_first(x,'floor','etage'),'type':_first(x,'propertyType','property_type','type_bien',default='Appartement'),'description':_first(x,'description','descriptionText'),'furnished':bool(_first(x,'furnished','meuble',default=False)),'dpe':_first(x,'dpeRating','dpeClass','energyClass','dpe_classe','dpe'),'ges':_first(x,'gesRating','gesClass','ges_classe','ges'),'heating':_first(x,'heatingType','heating_type'),'features':_first(x,'features','amenities','amenities_str',default=[]),'latitude':_first(x,'latitude','lat',default=None),'longitude':_first(x,'longitude','lng','lon',default=None),'agency':_first(x,'agencyName','agency_name'),'transaction_type':_first(x,'transactionType','transaction_type'),'price_per_m2':_first(x,'pricePerM2','price_per_m2',default=None),'photos':_photos(x),'source_url':_first(x,'url','listingUrl',default=url),'source':'seloger.com'}

def _raw(url):
 try:
  data=parse_url(url)
  if isinstance(data,dict) and data.get('title') and data.get('price') not in (None,'',0):
   if isinstance(data.get('photos'),str):
    try:data['photos']=json.loads(data['photos'])
    except Exception:data['photos']=[]
   data['source_url']=data.get('source_url') or url
   return data
 except Exception as first_error:
  if not APIFY_TOKEN: raise first_error
 if APIFY_TOKEN:
  data=_normalize(_apify(url),url)
  if data.get('title') or data.get('price') or data.get('description'): return data
 raise ValueError('Impossible de récupérer cette annonce. Le site ne renvoie pas suffisamment de données publiques.')

def _ai(raw):
 try:
  out=normalize_listing(raw)
  if not isinstance(out,dict): return raw
  for k in ('city','postal_code','address','latitude','longitude','price','surface','rooms','bedrooms'):
   if raw.get(k) not in (None,'',0,[]): out[k]=raw[k]
  out['photos']=raw.get('photos',[]);out['source_url']=raw.get('source_url') or ''
  return out
 except Exception:return raw

def _ensure_schema(c):
 for sql in ('ALTER TABLE listings ADD COLUMN photos TEXT','ALTER TABLE listings ADD COLUMN import_data TEXT','ALTER TABLE listings ADD COLUMN postal_code TEXT','ALTER TABLE listings ADD COLUMN address TEXT','ALTER TABLE listings ADD COLUMN bedrooms INTEGER','ALTER TABLE listings ADD COLUMN floor TEXT','ALTER TABLE listings ADD COLUMN dpe TEXT','ALTER TABLE listings ADD COLUMN ges TEXT'):
  try:c.execute(sql)
  except Exception:pass

def _download_photos(lid, urls):
 root=os.path.join(os.environ.get('LOGEO_DATA_DIR','/data'),'listing_photos',str(lid));os.makedirs(root,exist_ok=True)
 local=[]
 for i,url in enumerate(urls or [],1):
  try:
   req=urllib.request.Request(str(url),headers={'User-Agent':'Mozilla/5.0','Accept':'image/avif,image/webp,image/jpeg,image/png,*/*'})
   with urllib.request.urlopen(req,timeout=20) as r:data=r.read(12*1024*1024)
   if not data:continue
   c=r.headers.get_content_type() if hasattr(r.headers,'get_content_type') else 'image/jpeg';ext={ 'image/png':'png','image/webp':'webp','image/gif':'gif'}.get(c,'jpg')
   name=f'{i:03d}.{ext}';open(os.path.join(root,name),'wb').write(data);local.append(f'/listing-media/{lid}/{name}')
  except Exception:continue
 return local

@logeo.app.get('/listing-media/<int:lid>/<path:name>')
def listing_media(lid,name):
 root=os.path.join(os.environ.get('LOGEO_DATA_DIR','/data'),'listing_photos',str(lid))
 return send_from_directory(root,name)

@logeo.app.post('/api/import-preview')
def import_preview():
 try:
  u=logeo.user()
  if not u:return jsonify(error='Connexion requise'),401
  if u['role']!='owner':return jsonify(error='Import réservé aux propriétaires / agences'),403
  url=str((request.get_json(silent=True) or {}).get('url') or '').strip()
  if not url:return jsonify(error='Colle le lien de l’annonce'),400
  if 'seloger.com' not in url.lower():return jsonify(error='Pour cet importateur, utilise un lien SeLoger.'),400
  raw=_raw(url);preview=_ai(raw)
  # Keep a complete source snapshot alongside the AI-corrected text. Nothing is discarded.
  preview['_source_snapshot']=raw
  return jsonify(ok=True,preview=preview)
 except Exception as e:return jsonify(error=f'Import SeLoger : {e}'),422

@logeo.app.post('/api/import-clone')
def import_clone():
 try:
  u=logeo.user()
  if not u or u['role']!='owner':return jsonify(error='Connexion propriétaire requise'),403
  p=request.get_json(silent=True) or {};d=p.get('preview') or {};source=d.get('_source_snapshot') or d
  if not isinstance(source,dict):return jsonify(error='Données d’import invalides'),400
  title=d.get('title') or source.get('title') or 'Annonce importée';city=source.get('city') or d.get('city') or '';price=source.get('price') or d.get('price') or 0;surface=source.get('surface') or d.get('surface') or 0;typ=source.get('type') or d.get('type') or 'Appartement'
  if not city or not price:return jsonify(error='Ville ou prix manquant dans l’annonce source'),422
  photos=source.get('photos') or d.get('photos') or [];photos=photos if isinstance(photos,list) else []
  description=d.get('description') or source.get('description') or ''
  c=logeo.db();_ensure_schema(c)
  canonical=source.get('source_url') or d.get('source_url')
  existing=c.execute('SELECT id FROM listings WHERE source_url=?',(canonical,)).fetchone() if canonical else None
  if existing:return jsonify(ok=True,duplicate=True,id=existing['id'],photo_count=0)
  cur=c.execute('INSERT INTO listings(title,city,price,surface,type,distance_km,furnished,available_date,source,source_url,description,owner_id,created_at,photos,import_data,postal_code,address,bedrooms,floor,dpe,ges) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',(title,city,float(price),float(surface or 0),typ,0,1 if d.get('furnished',source.get('furnished',False)) else 0,source.get('available_date'),source.get('source','seloger.com'),canonical,description,u['id'],__import__('datetime').datetime.utcnow().isoformat(),json.dumps(photos,ensure_ascii=False),json.dumps(source,ensure_ascii=False),source.get('postal_code') or d.get('postal_code'),source.get('address') or d.get('address'),source.get('bedrooms') or d.get('bedrooms'),source.get('floor') or d.get('floor'),source.get('dpe') or d.get('dpe'),source.get('ges') or d.get('ges')))
  lid=cur.lastrowid;local=_download_photos(lid,photos)
  c.execute('UPDATE listings SET photos=? WHERE id=?',(json.dumps(local or photos,ensure_ascii=False),lid));c.commit();c.close()
  return jsonify(ok=True,duplicate=False,id=lid,photo_count=len(local or photos),photos=local or photos)
 except Exception as e:return jsonify(error=f'Clonage LOGEO : {type(e).__name__}'),422
