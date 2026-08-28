import os, json, re, urllib.parse, urllib.request
from flask import jsonify
import app as logeo

# Robust enrichment endpoint loaded before the legacy enrichment module.
_FIELDS = {
    'source_reference':'TEXT','latitude':'REAL','longitude':'REAL','price_per_m2':'REAL',
    'land_surface':'REAL','living_room_surface':'REAL','year_built':'INTEGER',
    'shower_rooms':'REAL','toilets':'REAL','kitchen':'TEXT','pool':'INTEGER','exclusive':'INTEGER',
    'legal_info':'TEXT','dpe_chart_url':'TEXT','ges_chart_url':'TEXT','virtual_tour_url':'TEXT',
    'video_url':'TEXT','published_at':'TEXT','seller_type':'TEXT','seller_name':'TEXT',
    'real_estate_network':'TEXT','region':'TEXT','department':'TEXT','listing_features':'TEXT',
    'floor':'TEXT','bedrooms':'REAL','bathrooms':'REAL','rooms':'REAL','dpe_class':'TEXT',
    'dpe_value':'REAL','ghg_class':'TEXT','ghg_value':'REAL','parking':'INTEGER','garage':'INTEGER',
    'balcony':'INTEGER','terrace':'INTEGER','garden':'INTEGER','cellar':'INTEGER','elevator':'INTEGER',
    'postal_code':'TEXT','tenant_fees':'REAL','charges':'REAL','deposit':'REAL','photos':'TEXT'
}

def _ensure_schema():
    c=logeo.db()
    for n,t in _FIELDS.items():
        try: c.execute(f'ALTER TABLE listings ADD COLUMN {n} {t}')
        except Exception: pass
    c.commit(); c.close()

_ensure_schema()

def _api_detail(source, reference):
    key=os.environ.get('CHERCHER_TROUVER_API_KEY','').strip()
    if not key: return {}
    url='https://cherchertrouver.immo/api/v1/annonces/{}/{}'.format(
        urllib.parse.quote(str(source),safe=''), urllib.parse.quote(str(reference),safe=''))
    req=urllib.request.Request(url,headers={'X-Api-Key':key,'Accept':'application/json','User-Agent':'LOGEO/1.0'})
    with urllib.request.urlopen(req,timeout=20) as r:
        data=json.loads(r.read().decode('utf-8'))
    return data.get('annonce',data) if isinstance(data,dict) else {}

def _first(d,*names):
    for n in names:
        v=d.get(n)
        if v not in (None,'',[]): return v
    return None

def _bool(v):
    if isinstance(v,bool): return 1 if v else 0
    if v is None or v=='': return None
    s=str(v).strip().lower()
    if s in ('1','true','yes','oui','on'): return 1
    if s in ('0','false','no','non','off'): return 0
    return None

def _derive(description, item):
    t=(description or '').lower(); out={}
    if item.get('floor') in (None,'') and re.search(r'\brez[ -]?de[ -]?chauss[ée]e?\b|\brdc\b',t): out['floor']='Rez-de-chaussée'
    if item.get('furnished') in (None,'') and re.search(r'\bmeubl[ée]e?\b',t): out['furnished']=1
    if item.get('toilets') in (None,''):
        m=re.search(r'(\d+)\s*(?:wc|toilettes?)\b',t)
        if m: out['toilets']=float(m.group(1))
    if item.get('bedrooms') in (None,''):
        m=re.search(r'(\d+)\s*(?:chambre|chambres)\b',t)
        if m: out['bedrooms']=float(m.group(1))
    if item.get('shower_rooms') in (None,''):
        m=re.search(r'(\d+)\s*(?:salle[s]?\s+d[’\']eau|salle[s]?\s+de\s+douche)',t)
        if m: out['shower_rooms']=float(m.group(1))
    if item.get('kitchen') in (None,''):
        if 'cuisine intégrée' in t or 'cuisine équipée' in t or 'cuisine equipee' in t: out['kitchen']='Intégrée / équipée'
        elif 'cuisine aménagée' in t: out['kitchen']='Aménagée'
        elif 'cuisine' in t: out['kitchen']='Cuisine'
    return out

def _features(a):
    out=[]
    for k,label in [('floor','Étage'),('toilets','WC'),('shower_rooms','Salle de douche'),('bathrooms','Salle de bains'),('kitchen','Cuisine')]:
        if a.get(k) not in (None,''): out.append(f'{label}: {a[k]}')
    for k,label in [('furnished','Meublé'),('balcony','Balcon'),('terrace','Terrasse'),('parking','Parking'),('garage','Garage'),('cellar','Cave'),('elevator','Ascenseur'),('garden','Jardin')]:
        v=_bool(a.get(k))
        if v is not None: out.append(label if v else 'Pas de '+label.lower())
    return out

def _save(listing_id, item):
    aliases={
      'source_reference':['source_reference','reference'],'latitude':['latitude'],'longitude':['longitude'],
      'price':['price'],'surface':['surface'],'type':['type'],'city':['city'],'title':['title'],
      'price_per_m2':['price_per_m2'],'land_surface':['land_surface'],'living_room_surface':['living_room_surface'],
      'year_built':['year_built'],'shower_rooms':['shower_rooms'],'toilets':['toilets'],'kitchen':['kitchen'],
      'pool':['pool'],'exclusive':['exclusive'],'legal_info':['legal_info'],'dpe_chart_url':['dpe_chart_url'],
      'ges_chart_url':['ges_chart_url'],'virtual_tour_url':['virtual_tour_url'],'video_url':['video_url'],
      'published_at':['published_at'],'seller_type':['seller_type'],'seller_name':['seller_name'],
      'real_estate_network':['real_estate_network'],'region':['region'],'department':['department'],
      'description':['description','descriptif','texte'],'floor':['floor','etage','étage'],
      'furnished':['furnished','meuble','meublé'],'available_date':['available_date','availability_date','available_from','disponible_le'],
      'bedrooms':['bedrooms','chambres'],'bathrooms':['bathrooms','salles_de_bains'],'rooms':['rooms','pieces','pièces'],
      'dpe_class':['dpe_class','dpe'],'dpe_value':['dpe_value'],'ghg_class':['ghg_class','ges'],'ghg_value':['ghg_value','ges_value'],
      'parking':['parking'],'garage':['garage'],'balcony':['balcony'],'terrace':['terrace'],'garden':['garden'],
      'cellar':['cellar'],'elevator':['elevator'],'postal_code':['postal_code','cp','postcode'],
      'tenant_fees':['tenant_fees','frais_locataire','honoraires_locataire'],'charges':['charges','monthly_charges'],
      'deposit':['deposit','depot_garantie','dépôt_garantie'],'photos':['photos','images']}
    fields={}
    for target,names in aliases.items():
        v=_first(item,*names)
        if v not in (None,''): fields[target]=v
    fields.update({k:v for k,v in _derive(fields.get('description',''),fields).items() if fields.get(k) in (None,'')})
    for k in ('furnished','balcony','terrace','parking','garage','garden','cellar','elevator','pool','exclusive'):
        if k in fields: fields[k]=_bool(fields[k])
    if 'photos' in fields and isinstance(fields['photos'],(list,dict)): fields['photos']=json.dumps(fields['photos'],ensure_ascii=False)
    fields['listing_features']=json.dumps(_features(fields),ensure_ascii=False)
    c=logeo.db(); sets=[]; vals=[]
    for k,v in fields.items():
        sets.append(f'{k}={"%s" if logeo.USE_PG else "?"}'); vals.append(v)
    if sets:
        vals.append(listing_id)
        c.execute('UPDATE listings SET '+','.join(sets)+(' WHERE id=%s' if logeo.USE_PG else ' WHERE id=?'),vals)
        c.commit()
    row=c.execute(logeo.ph('SELECT * FROM listings WHERE id=?'),(listing_id,)).fetchone(); c.close()
    return dict(row) if row else None

@logeo.app.post('/api/owner/enrich-listing/<int:listing_id>')
def enrich_listing_fixed(listing_id):
    u=logeo.require_role('owner')
    if not u: return jsonify(error='Connexion propriétaire requise'),401
    if u is False: return jsonify(error='Compte étudiant'),403
    c=logeo.db(); row=c.execute(logeo.ph('SELECT * FROM listings WHERE id=? AND owner_id=?'),(listing_id,u['id'])).fetchone(); c.close()
    if not row: return jsonify(error='Annonce introuvable'),404
    source=row['source'] if 'source' in row.keys() else None
    reference=row['source_reference'] if 'source_reference' in row.keys() else None
    if not source or not reference: return jsonify(ok=True,listing=dict(row),enriched=False)
    try: item=_api_detail(source,reference)
    except Exception as exc:
        print('LOGEO enrichment API error:',exc)
        return jsonify(ok=True,listing=dict(row),enriched=False)
    if not item: return jsonify(ok=True,listing=dict(row),enriched=False)
    merged=dict(row); merged.update(item)
    merged['description']=_first(item,'description','descriptif','texte') or merged.get('description') or ''
    for k,v in _derive(merged['description'],merged).items():
        if merged.get(k) in (None,''): merged[k]=v
    try: saved=_save(listing_id,merged)
    except Exception as exc:
        print('LOGEO enrichment DB error:',exc)
        return jsonify(error='Erreur de sauvegarde des données enrichies'),500
    return jsonify(ok=True,enriched=True,listing=saved)
