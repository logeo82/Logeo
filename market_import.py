import json, os, urllib.parse, urllib.request, re
from flask import jsonify, request
import app as logeo
BASE='https://cherchertrouver.immo/api/v1'
def _photos(item):
 p=item.get('images',item.get('photos',item.get('pictures',[])))
 if isinstance(p,str):
  try:p=json.loads(p)
  except Exception:p=[]
 return p if isinstance(p,list) else []
def _detail(source, reference):
 key=os.environ.get('CHERCHER_TROUVER_API_KEY','').strip()
 if not key or not source or not reference:return {}
 path=f"{BASE}/annonces/{urllib.parse.quote(str(source).strip(),safe='')}/{urllib.parse.quote(str(reference).strip(),safe='')}"
 headers={'X-Api-Key':key,'Accept':'application/json','User-Agent':'LOGEO/1.2'}
 for mode in ('key','bearer'):
  try:
   h=dict(headers)
   if mode=='bearer':h.pop('X-Api-Key',None);h['Authorization']='Bearer '+key
   with urllib.request.urlopen(urllib.request.Request(path,headers=h),timeout=20) as r:raw=json.loads(r.read().decode('utf-8'))
   if isinstance(raw,dict):
    for k in ('annonce','item','data','listing'):
     if isinstance(raw.get(k),dict):return raw[k]
    return raw
  except Exception:continue
 return {}
def _first(d,*names):
 for n in names:
  v=d.get(n) if isinstance(d,dict) else None
  if v not in (None,'',[],{}):return v
 return None
def _derive(item):
 text=str(item.get('description') or item.get('descriptif') or item.get('texte') or '').lower();o={}
 if item.get('floor') in (None,'') and re.search(r'\brez[ -]?de[ -]?chauss[ée]e?\b|\brdc\b',text):o['floor']='Rez-de-chaussée'
 if item.get('furnished') in (None,'') and re.search(r'\bmeubl[ée]e?\b',text):o['furnished']=1
 if item.get('toilets') in (None,''):
  m=re.search(r'(\d+)\s*(?:wc|toilettes?)\b',text)
  if m:o['toilets']=float(m.group(1))
 if item.get('shower_rooms') in (None,''):
  m=re.search(r'(\d+)\s*(?:salle[s]?\s+d[’\']eau|salle[s]?\s+de\s+douche)',text)
  if m:o['shower_rooms']=float(m.group(1))
 if item.get('kitchen') in (None,''):
  if 'cuisine intégrée' in text or 'cuisine équipée' in text or 'cuisine equipee' in text:o['kitchen']='Intégrée / équipée'
  elif 'cuisine aménagée' in text:o['kitchen']='Aménagée'
 if item.get('balcony') in (None,'') and re.search(r'\bpas de balcon\b|\bsans balcon\b',text):o['balcony']=0
 return o
def _merge_detail(item,source,reference):
 detail=_detail(source,reference);merged=dict(item or {})
 if detail:
  for k,v in detail.items():
   if v not in (None,'',[],{}):merged[k]=v
  aliases={'floor':['floor','etage','étage','floor_number','floor_label'],'total_floors':['total_floors','nombre_etages','number_of_floors'],'furnished':['furnished','meuble','meublé','is_furnished'],'available_date':['available_date','availability_date','available_from','available_at','disponible_le','date_disponibilite'],'description':['description','descriptif','texte','ad_text','listing_description','description_text'],'bedrooms':['bedrooms','chambres','bedroom_count','nb_chambres'],'bathrooms':['bathrooms','salles_de_bains','sdb','bathroom_count','nb_sdb'],'rooms':['rooms','pieces','pièces','room_count'],'dpe':['dpe','dpe_class','energy_class'],'ges':['ges','ghg_class','greenhouse_class'],'shower_rooms':['shower_rooms','salles_de_douche'],'toilets':['toilets','wc','toilettes'],'kitchen':['kitchen','cuisine'],'tenant_fees':['tenant_fees','honoraires_locataire'],'charges':['charges','provision_charges'],'deposit':['deposit','depot_garantie'],'latitude':['latitude'],'longitude':['longitude'],'price_per_m2':['price_per_m2'],'parking':['parking','stationnement'],'garage':['garage'],'terrace':['terrace','terrasse'],'balcony':['balcony','balcon'],'garden':['garden','jardin'],'cellar':['cellar','cave'],'elevator':['elevator','ascenseur'],'address':['address','adresse'],'neighborhood':['neighborhood','quartier']}
  for target,names in aliases.items():
   v=_first(detail,*names)
   if v not in (None,'',[],{}):merged[target]=v
  for container_name in ('characteristics','features','details','property'):
   sub=detail.get(container_name)
   if isinstance(sub,dict):
    for target,names in aliases.items():
     if merged.get(target) in (None,'','[]'):
      v=_first(sub,*names)
      if v not in (None,'',[],{}):merged[target]=v
 for k,v in _derive(merged).items():
  if merged.get(k) in (None,''):merged[k]=v
 return merged
def _payload(item,source,external):
 return {'listing_kind':'sale' if str(item.get('transaction_type','')).lower() in ('vente','sale','sell') else 'location','title':item.get('title') or 'Annonce immobilière','city':item.get('city') or '','postal_code':item.get('postal_code'),'address':item.get('address'),'neighborhood':item.get('neighborhood'),'price':item.get('price') or 0,'surface':item.get('surface') or 0,'type':item.get('type') or 'Appartement','rooms':item.get('rooms'),'bedrooms':item.get('bedrooms'),'bathrooms':item.get('bathrooms'),'parking':item.get('parking'),'cellar':item.get('cellar'),'garden':item.get('garden'),'elevator':item.get('elevator'),'balcony':item.get('balcony'),'terrace':item.get('terrace'),'garage':item.get('garage'),'floor':item.get('floor'),'total_floors':item.get('total_floors'),'heating':item.get('heating'),'heating_type':item.get('heating_type'),'air_conditioning':item.get('air_conditioning'),'double_glazing':item.get('double_glazing'),'internet_fiber':item.get('internet_fiber'),'dpe_class':item.get('dpe_class') or item.get('dpe'),'dpe_value':item.get('dpe_value'),'ghg_class':item.get('ghg_class') or item.get('ges'),'ghg_value':item.get('ghg_value'),'description':item.get('description') or item.get('descriptif') or item.get('texte') or '','photos':_photos(item)[:30],'source':source,'source_reference':item.get('reference') or None,'source_url':external,'furnished':item.get('furnished',False),'available_date':item.get('available_date'),'tenant_fees':item.get('tenant_fees'),'charges':item.get('charges'),'deposit':item.get('deposit'),'shower_rooms':item.get('shower_rooms'),'toilets':item.get('toilets'),'kitchen':item.get('kitchen'),'latitude':item.get('latitude'),'longitude':item.get('longitude'),'price_per_m2':item.get('price_per_m2'),'land_surface':item.get('land_surface'),'living_room_surface':item.get('living_room_surface'),'year_built':item.get('year_built'),'pool':item.get('pool'),'exclusive':item.get('exclusive'),'legal_info':item.get('legal_info'),'dpe_chart_url':item.get('dpe_chart_url'),'ges_chart_url':item.get('ges_chart_url'),'virtual_tour_url':item.get('virtual_tour_url'),'video_url':item.get('video_url'),'published_at':item.get('published_at'),'seller_type':item.get('seller_type'),'seller_name':item.get('seller_name'),'real_estate_network':item.get('real_estate_network'),'region':item.get('region'),'department':item.get('department')}
def _update_existing(c,existing,payload):
 updates=[];values=[]
 for field in ('source_reference','description','floor','total_floors','furnished','available_date','bedrooms','bathrooms','shower_rooms','toilets','kitchen','photos','dpe_class','dpe_value','ghg_class','ghg_value','postal_code','address','neighborhood','heating','heating_type','parking','garage','balcony','terrace','garden','cellar','elevator','latitude','longitude','price_per_m2','land_surface','living_room_surface','year_built','pool','exclusive','legal_info','dpe_chart_url','ges_chart_url','virtual_tour_url','video_url','published_at','seller_type','seller_name','real_estate_network','region','department','tenant_fees','charges','deposit'):
  value=payload.get(field)
  if value not in (None,'',[],{}):
   if field=='photos':value=json.dumps(value,ensure_ascii=False)
   updates.append(f'{field}=?');values.append(value)
 if not updates:return
 values.append(existing['id']);c.execute(logeo.ph('UPDATE listings SET '+','.join(updates)+' WHERE id=?'),values);c.commit()
def _refresh_existing_description(listing_id, source, reference, row):
 try:
  import description_refresh as dr
  detail=dr._detail(source,reference)
  if not detail:return False
  api_desc=dr._description(detail)
  external_desc=dr._external_description(dr._external_url(detail,row))
  current=str(row['description'] or '') if 'description' in row.keys() else ''
  candidates=[x for x in (api_desc,external_desc,current) if x and str(x).strip()]
  if not candidates:return False
  best=max(candidates,key=lambda x:len(str(x)))
  if len(best)<=len(current):return False
  merged=dict(row);merged['description']=best
  for k,v in dr.le._derive(best,merged).items():
   if merged.get(k) in (None,''):merged[k]=v
  dr.le._update(listing_id,merged)
  print(f'LOGEO: existing listing {listing_id} description refreshed ({len(current)} -> {len(best)} chars)')
  return True
 except Exception as exc:
  print(f'LOGEO: existing listing description refresh failed: {type(exc).__name__}: {exc}')
  return False
@logeo.app.post('/api/market-import')
def market_import():
 u=logeo.user()
 if not u or u['role']!='owner':return jsonify(error='Connexion propriétaire requise'),403
 x=request.get_json(silent=True) or {};source=str(x.get('source') or '').strip();reference=str(x.get('reference') or '').strip();item=x.get('listing') if isinstance(x.get('listing'),dict) else None
 try:
  if not item and source and reference:
   import market_search;item=market_search.cached_listing(source,reference)
  if not item:return jsonify(error='Annonce non disponible en mémoire. Relance la recherche puis réessaie.'),404
  source=str(item.get('source') or source);reference=str(item.get('reference') or reference);item=_merge_detail(item,source,reference)
  external=item.get('external_url')
  if not external:
   for s in (item.get('sources') or []):
    if isinstance(s,dict) and s.get('url') and (not source or s.get('source')==source):external=s['url'];break
  if not external and item.get('sources') and isinstance(item['sources'][0],dict):external=item['sources'][0].get('url')
  c=logeo.db()
  try:
   existing=c.execute(logeo.ph('SELECT * FROM listings WHERE source_url=?'),(external,)).fetchone() if external else None
   if existing:
    payload=_payload(item,source,external);_update_existing(c,existing,payload)
    row=c.execute(logeo.ph('SELECT * FROM listings WHERE id=?'),(existing['id'],)).fetchone()
    refreshed=_refresh_existing_description(existing['id'],source,reference,row)
    row=c.execute(logeo.ph('SELECT * FROM listings WHERE id=?'),(existing['id'],)).fetchone()
    return jsonify(ok=True,duplicate=True,enriched=refreshed,id=existing['id'],listing=dict(row))
  finally:c.close()
  import owner_extended
  return owner_extended._insert(_payload(item,source,external),u)
 except Exception as e:return jsonify(error=f'Import ChercherTrouver impossible : {type(e).__name__}: {e}'),500
