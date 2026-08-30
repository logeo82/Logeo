import json, os, urllib.parse, urllib.request, re, time
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
 for attempt in range(3):
  for mode in ('key','bearer'):
   try:
    h=dict(headers)
    if mode=='bearer':h.pop('X-Api-Key',None);h['Authorization']='Bearer '+key
    with urllib.request.urlopen(urllib.request.Request(path,headers=h),timeout=20) as r:raw=json.loads(r.read().decode('utf-8'))
    if isinstance(raw,dict):
     for k in ('annonce','item','data','listing','result'):
      if isinstance(raw.get(k),dict):return raw[k]
     return raw
   except urllib.error.HTTPError as exc:
    if exc.code==429:
     try:delay=min(max(float(exc.headers.get('Retry-After','2')),1.1),10)
     except Exception:delay=2.0
     time.sleep(delay)
    else:continue
   except Exception:continue
 return {}
def _first(d,*names):
 for n in names:
  v=d.get(n) if isinstance(d,dict) else None
  if v not in (None,'',[],{}):return v
 return None
def _description(d):
 names={'description','description_full','full_description','description_long','long_description','descriptif','texte','ad_text','listing_description','description_text','content','body','description_html'}
 found=[]
 def walk(x):
  if isinstance(x,dict):
   for k,v in x.items():
    kl=str(k).lower()
    if kl in names and isinstance(v,str) and v.strip():found.append(v)
    elif kl in names and isinstance(v,dict):
     for kk in ('text','html','content','value'):
      if isinstance(v.get(kk),str) and v.get(kk).strip():found.append(v[kk])
    if isinstance(v,(dict,list)):walk(v)
  elif isinstance(x,list):
   for v in x:walk(v)
 walk(d)
 cleaned=[]
 for v in found:
  v=re.sub(r'<br\s*/?>','\n',v,flags=re.I);v=re.sub(r'</p\s*>','\n\n',v,flags=re.I);v=re.sub(r'<[^>]+>','',v);v=re.sub(r'\n{3,}','\n\n',__import__('html').unescape(v)).strip()
  if v and v not in cleaned:cleaned.append(v)
 return max(cleaned,key=len) if cleaned else ''
def _derive(item):
 text=str(item.get('description') or item.get('descriptif') or item.get('texte') or '').lower();o={}
 if item.get('floor') in (None,'') and re.search(r'\brez[ -]?de[ -]?chauss[ée]e?\b|\brdc\b',text):o['floor']='Rez-de-chaussée'
 if item.get('furnished') in (None,'') and re.search(r'\bmeubl[ée]e?\b',text):o['furnished']=1
 if item.get('toilets') in (None,''):
  m=re.search(r'(\d+)\s*(?:wc|toilettes?)\b',text)
  if m:o['toilets']=float(m.group(1))
 return o
def _duplicate_descriptions(detail,source,reference):
 out=[];sources=detail.get('sources') if isinstance(detail,dict) else None
 if not isinstance(sources,list):return out
 seen={(str(source),str(reference))}
 for s in sources:
  if not isinstance(s,dict):continue
  src=str(s.get('source') or '').strip();ref=str(s.get('reference') or '').strip()
  if not src or not ref or (src,ref) in seen:continue
  seen.add((src,ref));time.sleep(1.1);d=_detail(src,ref);desc=_description(d)
  if desc:out.append((desc,d));print(f'LOGEO: duplicate {src}/{ref} description={len(desc)} chars')
 return out
def _merge_detail(item,source,reference):
 detail=_detail(source,reference);merged=dict(item or {})
 if detail:
  for k,v in detail.items():
   if v not in (None,'',[],{}):merged[k]=v
  aliases={'description':['description','description_full','full_description','description_long','descriptif','texte','ad_text','listing_description','description_text','description_html'],'floor':['floor','etage','étage','floor_number','floor_label'],'total_floors':['total_floors','nombre_etages','number_of_floors'],'furnished':['furnished','meuble','meublé','is_furnished'],'available_date':['available_date','availability_date','available_from','available_at','disponible_le','date_disponibilite'],'bedrooms':['bedrooms','chambres','bedroom_count','nb_chambres'],'bathrooms':['bathrooms','salles_de_bains','sdb','bathroom_count','nb_sdb'],'rooms':['rooms','pieces','pièces','room_count'],'dpe':['dpe','dpe_class','energy_class'],'ges':['ges','ghg_class','greenhouse_class'],'shower_rooms':['shower_rooms','salles_de_douche'],'toilets':['toilets','wc','toilettes'],'kitchen':['kitchen','cuisine'],'tenant_fees':['tenant_fees','honoraires_locataire'],'charges':['charges','provision_charges'],'deposit':['deposit','depot_garantie'],'latitude':['latitude'],'longitude':['longitude'],'price_per_m2':['price_per_m2'],'parking':['parking','stationnement'],'garage':['garage'],'terrace':['terrace','terrasse'],'balcony':['balcony','balcon'],'garden':['garden','jardin'],'cellar':['cellar','cave'],'elevator':['elevator','ascenseur'],'address':['address','adresse'],'neighborhood':['neighborhood','quartier']}
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
 if not merged.get('description'):merged['description']=_description(detail)
 for k,v in _derive(merged).items():
  if merged.get(k) in (None,''):merged[k]=v
 return merged
def _payload(item,source,external):
 return {'listing_kind':'sale' if str(item.get('transaction_type','')).lower() in ('vente','sale','sell') else 'location','title':item.get('title') or 'Annonce immobilière','city':item.get('city') or '','postal_code':item.get('postal_code'),'address':item.get('address'),'neighborhood':item.get('neighborhood'),'price':item.get('price') or 0,'surface':item.get('surface') or 0,'type':item.get('type') or 'Appartement','rooms':item.get('rooms'),'bedrooms':item.get('bedrooms'),'bathrooms':item.get('bathrooms'),'parking':item.get('parking'),'cellar':item.get('cellar'),'garden':item.get('garden'),'elevator':item.get('elevator'),'balcony':item.get('balcony'),'terrace':item.get('terrace'),'garage':item.get('garage'),'floor':item.get('floor'),'total_floors':item.get('total_floors'),'heating':item.get('heating'),'heating_type':item.get('heating_type'),'air_conditioning':item.get('air_conditioning'),'double_glazing':item.get('double_glazing'),'internet_fiber':item.get('internet_fiber'),'dpe_class':item.get('dpe_class') or item.get('dpe'),'dpe_value':item.get('dpe_value'),'ghg_class':item.get('ghg_class') or item.get('ges'),'ghg_value':item.get('ghg_value'),'description':_description(item) or item.get('description') or item.get('descriptif') or item.get('texte') or '','photos':_photos(item)[:30],'source':source,'source_reference':item.get('reference') or None,'source_url':external,'furnished':item.get('furnished',False),'available_date':item.get('available_date'),'tenant_fees':item.get('tenant_fees'),'charges':item.get('charges'),'deposit':item.get('deposit'),'shower_rooms':item.get('shower_rooms'),'toilets':item.get('toilets'),'kitchen':item.get('kitchen'),'latitude':item.get('latitude'),'longitude':item.get('longitude'),'price_per_m2':item.get('price_per_m2'),'land_surface':item.get('land_surface'),'living_room_surface':item.get('living_room_surface'),'year_built':item.get('year_built'),'pool':item.get('pool'),'exclusive':item.get('exclusive'),'legal_info':item.get('legal_info'),'dpe_chart_url':item.get('dpe_chart_url'),'ges_chart_url':item.get('ges_chart_url'),'virtual_tour_url':item.get('virtual_tour_url'),'video_url':item.get('video_url'),'published_at':item.get('published_at'),'seller_type':item.get('seller_type'),'seller_name':item.get('seller_name'),'real_estate_network':item.get('real_estate_network'),'region':item.get('region'),'department':item.get('department')}
def _bool_int(v):return 1 if v is True or str(v).lower() in ('1','true','yes','oui','on') else 0 if v is False or str(v).lower() in ('0','false','no','non','off') else v
def _update_existing(c,existing,payload):
 updates=[];values=[]
 for field in ('source_reference','description','floor','total_floors','furnished','available_date','bedrooms','bathrooms','shower_rooms','toilets','kitchen','photos','dpe_class','dpe_value','ghg_class','ghg_value','postal_code','address','neighborhood','heating','heating_type','parking','garage','balcony','terrace','garden','cellar','elevator','latitude','longitude','price_per_m2','land_surface','living_room_surface','year_built','pool','exclusive','legal_info','dpe_chart_url','ges_chart_url','virtual_tour_url','video_url','published_at','seller_type','seller_name','real_estate_network','region','department','tenant_fees','charges','deposit'):
  value=payload.get(field)
  if value not in (None,'',[],{}):
   if field=='photos':value=json.dumps(value,ensure_ascii=False)
   if field in ('furnished','parking','garage','balcony','terrace','garden','cellar','elevator','pool','exclusive'):value=_bool_int(value)
   updates.append(f'{field}=?');values.append(value)
 if not updates:return
 values.append(existing['id']);c.execute(logeo.ph('UPDATE listings SET '+','.join(updates)+' WHERE id=?'),values);c.commit()
def _refresh_existing_description(listing_id,source,reference,row):
 detail=_detail(source,reference)
 if not detail:return False
 current=str(row['description'] or '') if 'description' in row.keys() else ''
 candidates=[(_description(detail),detail)]
 candidates.extend(_duplicate_descriptions(detail,source,reference))
 candidates=[x for x in candidates if x[0]]
 if not candidates:return False
 best,best_detail=max(candidates,key=lambda x:len(x[0]))
 if len(best)<=len(current):print(f'LOGEO: existing listing {listing_id} description unchanged ({len(current)} chars; API best={len(best)})');return False
 import listing_enrichment as le
 merged=dict(row);merged['description']=best
 for k,v in best_detail.items():
  if merged.get(k) in (None,'',[]):merged[k]=v
 for k,v in _derive(merged).items():
  if merged.get(k) in (None,''):merged[k]=v
 le._update(listing_id,merged)
 print(f'LOGEO: existing listing {listing_id} description refreshed ({len(current)} -> {len(best)} chars)')
 return True
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
    return jsonify(ok=True,duplicate=True,enriched=refreshed,description_length=len(str(row['description'] or '')),id=existing['id'],listing=dict(row))
  finally:c.close()
  import owner_extended
  return owner_extended._insert(_payload(item,source,external),u)
 except Exception as e:return jsonify(error=f'Import ChercherTrouver impossible : {type(e).__name__}: {e}'),500
