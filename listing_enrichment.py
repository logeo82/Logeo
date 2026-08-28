import os, re, json, urllib.parse, urllib.request
from flask import jsonify
import app as logeo
BASE='https://cherchertrouver.immo/api/v1'
_FIELDS={'source_reference':'TEXT','latitude':'REAL','longitude':'REAL','price_per_m2':'REAL','land_surface':'REAL','living_room_surface':'REAL','year_built':'INTEGER','shower_rooms':'REAL','toilets':'REAL','kitchen':'TEXT','pool':'INTEGER','exclusive':'INTEGER','legal_info':'TEXT','dpe_chart_url':'TEXT','ges_chart_url':'TEXT','virtual_tour_url':'TEXT','video_url':'TEXT','published_at':'TEXT','seller_type':'TEXT','seller_name':'TEXT','real_estate_network':'TEXT','region':'TEXT','department':'TEXT','listing_features':'TEXT'}
def _ensure_schema():
 c=logeo.db()
 for n,s in _FIELDS.items():
  try:c.execute(f'ALTER TABLE listings ADD COLUMN {n} {s}')
  except Exception:pass
 c.commit();c.close()
_ensure_schema()
def _api_detail(source,reference):
 key=os.environ.get('CHERCHER_TROUVER_API_KEY','').strip()
 if not key:return {}
 p=f"{BASE}/annonces/{urllib.parse.quote(str(source),safe='')}/{urllib.parse.quote(str(reference),safe='')}"
 req=urllib.request.Request(p,headers={'X-Api-Key':key,'Accept':'application/json','User-Agent':'LOGEO/1.0'})
 with urllib.request.urlopen(req,timeout=20) as r:data=json.loads(r.read().decode('utf-8'))
 return data.get('annonce',data) if isinstance(data,dict) else {}
def _bool(v):
 if isinstance(v,bool):return 1 if v else 0
 if v is None:return None
 s=str(v).strip().lower()
 if s in ('1','true','yes','oui','on'):return 1
 if s in ('0','false','no','non','off'):return 0
 return None
def _first(d,*names):
 for n in names:
  v=d.get(n)
  if v not in (None,'',[]):return v
 return None
def _derive(text,item):
 t=(text or '').lower();o={}
 if item.get('floor') in (None,'') and re.search(r'\brez[ -]?de[ -]?chauss[ée]e?\b|\brdc\b',t):o['floor']='Rez-de-chaussée'
 if item.get('furnished') in (None,'') and re.search(r'\bmeubl[ée]e?\b',t):o['furnished']=1
 if item.get('toilets') in (None,''):
  m=re.search(r'(\d+)\s*(?:wc|toilettes?)\b',t)
  if m:o['toilets']=float(m.group(1))
 if item.get('shower_rooms') in (None,''):
  m=re.search(r'(\d+)\s*(?:salle[s]?\s+d[’\']eau|salle[s]?\s+de\s+douche)',t)
  if m:o['shower_rooms']=float(m.group(1))
 if item.get('kitchen') in (None,''):
  if 'cuisine intégrée' in t or 'cuisine équipée' in t or 'cuisine equipee' in t:o['kitchen']='Intégrée / équipée'
  elif 'cuisine aménagée' in t:o['kitchen']='Aménagée'
  elif 'cuisine' in t:o['kitchen']='Cuisine'
 if item.get('balcony') in (None,'') and re.search(r'\bpas de balcon\b|\bsans balcon\b',t):o['balcony']=0
 if item.get('bedrooms') in (None,''):
  m=re.search(r'(\d+)\s*(?:chambre|chambres)\b',t)
  if m:o['bedrooms']=float(m.group(1))
 return o
def _features(a):
 out=[]
 for k,label in [('floor','Étage'),('toilets','WC'),('shower_rooms','Salle de douche'),('bathrooms','Salle de bains'),('kitchen','Cuisine')]:
  v=a.get(k)
  if v not in (None,''):out.append(f'{label}: {v}')
 for k,label in [('furnished','Meublé'),('balcony','Balcon'),('terrace','Terrasse'),('parking','Parking'),('garage','Garage'),('cellar','Cave'),('elevator','Ascenseur'),('garden','Jardin')]:
  v=_bool(a.get(k))
  if v is not None:out.append(label if v else 'Pas de '+label.lower())
 return out
def _update(row_id,a):
 aliases={'source_reference':['reference'],'latitude':['latitude'],'longitude':['longitude'],'price_per_m2':['price_per_m2'],'land_surface':['land_surface'],'living_room_surface':['living_room_surface'],'year_built':['year_built'],'shower_rooms':['shower_rooms'],'toilets':['toilets'],'kitchen':['kitchen'],'pool':['pool'],'exclusive':['exclusive'],'legal_info':['legal_info'],'dpe_chart_url':['dpe_chart_url'],'ges_chart_url':['ges_chart_url'],'virtual_tour_url':['virtual_tour_url'],'video_url':['video_url'],'published_at':['published_at'],'seller_type':['seller_type'],'seller_name':['seller_name'],'real_estate_network':['real_estate_network'],'region':['region'],'department':['department'],'description':['description','descriptif','texte'],'floor':['floor','etage','étage'],'furnished':['furnished','meuble','meublé'],'available_date':['available_date','availability_date','available_from','disponible_le'],'bedrooms':['bedrooms','chambres'],'bathrooms':['bathrooms','salles_de_bains'],'rooms':['rooms','pieces','pièces'],'dpe_class':['dpe'],'dpe_value':['dpe_value'],'ghg_class':['ges'],'ghg_value':['ges_value'],'parking':['parking'],'garage':['garage'],'balcony':['balcony'],'terrace':['terrace'],'garden':['garden'],'cellar':['cellar'],'elevator':['elevator']}
 fields={}
 for target,names in aliases.items():
  v=_first(a,*names)
  if v not in (None,''):fields[target]=v
 if not fields.get('description'):fields['description']=a.get('description') or ''
 fields.update({k:v for k,v in _derive(fields.get('description',''),fields).items() if fields.get(k) in (None,'')})
 for k in ('furnished','balcony','terrace','parking','garage','garden','cellar','elevator','pool','exclusive'):
  if k in fields:fields[k]=_bool(fields[k])
 fields['listing_features']=json.dumps(_features(fields),ensure_ascii=False)
 c=logeo.db();sets=[];vals=[]
 for k,v in fields.items():sets.append(f'{k}={"%s" if logeo.USE_PG else "?"}');vals.append(v)
 if sets:
  vals.append(row_id);c.execute('UPDATE listings SET '+','.join(sets)+(' WHERE id=%s' if logeo.USE_PG else ' WHERE id=?'),vals);c.commit()
 row=c.execute(logeo.ph('SELECT * FROM listings WHERE id=?'),(row_id,)).fetchone();c.close();return dict(row) if row else None
@logeo.app.post('/api/owner/enrich-listing/<int:listing_id>')
def enrich_listing(listing_id):
 u=logeo.require_role('owner')
 if not u:return jsonify(error='Connexion propriétaire requise'),401
 if u is False:return jsonify(error='Compte étudiant'),403
 c=logeo.db();row=c.execute(logeo.ph('SELECT * FROM listings WHERE id=? AND owner_id=?'),(listing_id,u['id'])).fetchone();c.close()
 if not row:return jsonify(error='Annonce introuvable'),404
 source=row['source'] if 'source' in row.keys() else None;reference=row['source_reference'] if 'source_reference' in row.keys() else None
 if not source or not reference:return jsonify(ok=True,listing=dict(row),enriched=False)
 try:item=_api_detail(source,reference)
 except Exception:return jsonify(ok=True,listing=dict(row),enriched=False)
 if not item:return jsonify(ok=True,listing=dict(row),enriched=False)
 merged=dict(row);merged.update(item);merged['description']=_first(item,'description','descriptif','texte') or merged.get('description') or ''
 for k,v in _derive(merged['description'],merged).items():
  if merged.get(k) in (None,''):merged[k]=v
 return jsonify(ok=True,enriched=True,listing=_update(listing_id,merged))
@logeo.app.after_request
def inject_detail_ui(response):
 try:
  if response.content_type and response.content_type.startswith('text/html'):
   page=response.get_data(as_text=True)
   if 'id="ownerApp"' in page and 'listingEnrichmentUI' not in page:
    script=r'''<script id="listingEnrichmentUI">(function(){const E=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));function f(l,v){return v===null||v===undefined||v===''?'':'<div class="le-f"><span>'+E(l)+'</span><b>'+E(v)+'</b></div>'}async function open(id){let m=document.getElementById('leModal');if(!m){m=document.createElement('div');m.id='leModal';document.body.appendChild(m)}m.innerHTML='<div class="le-bg"><div class="le-sheet"><button class="le-x" onclick="document.getElementById(\'leModal\').remove()">×</button><p>Chargement de la fiche complète…</p></div></div>';try{const r=await fetch('/api/owner/enrich-listing/'+id,{method:'POST'}),x=await r.json(),a=x.listing||{};let imgs=[];try{imgs=typeof a.photos==='string'?JSON.parse(a.photos):a.photos||[]}catch(e){}const desc=a.description||'Description non disponible';const dpe=a.dpe_class||a.dpe||'Non communiqué',ges=a.ghg_class||a.ges||'Non communiqué';const pm2=a.price_per_m2||((+a.price||0)/(+a.surface||0)||0);let feats=[];try{feats=a.listing_features?JSON.parse(a.listing_features):[]}catch(e){}const map=a.latitude&&a.longitude?'<iframe class="le-map" src="https://www.openstreetmap.org/export/embed.html?bbox='+(+a.longitude-.01)+','+(+a.latitude-.01)+','+(+a.longitude+.01)+','+(+a.latitude+.01)+'&layer=mapnik&marker='+a.latitude+','+a.longitude+'"></iframe>':'';m.innerHTML='<div class="le-bg"><div class="le-sheet"><button class="le-x" onclick="document.getElementById(\'leModal\').remove()">×</button><header><div><small>ANNONCE LOGEO</small><h1>'+E(a.title||'Annonce')+'</h1><p>📍 '+E(a.city||'')+' · '+E(a.postal_code||'')+'</p></div><strong class="le-price">'+E(a.price||0)+' €</strong></header>'+(imgs.length?'<img class="le-main" id="leMain" src="'+E(imgs[0])+'"><div class="le-th">'+imgs.map(u=>'<img src="'+E(u)+'" onclick="document.getElementById(\'leMain\').src=this.src">').join('')+'</div>':'')+'<div class="le-grid">'+f('Surface',a.surface?(a.surface+' m²'):'—')+f('Pièces',a.rooms)+f('Chambres',a.bedrooms)+f('Salle de bains',a.bathrooms)+f('Salle de douche',a.shower_rooms)+f('WC',a.toilets)+f('Étage',a.floor||'—')+f('Meublé',a.furnished===1?'Oui':a.furnished===0?'Non':'—')+f('Disponibilité',a.available_date||'—')+f('Cuisine',a.kitchen||'—')+f('Prix / m²',pm2?Math.round(pm2)+' €/m²':'—')+f('DPE',dpe)+f('GES',ges)+f('Honoraires locataire',a.tenant_fees!=null?a.tenant_fees+' € TTC':'—')+f('Charges',a.charges!=null?a.charges+' €/mois':'—')+f('Dépôt de garantie',a.deposit!=null?a.deposit+' €':'—')+'</div><section><h2>Caractéristiques</h2><div class="le-chips">'+feats.map(v=>'<span>'+E(v)+'</span>').join('')+'</div></section><section><h2>Description complète</h2><div class="le-desc">'+E(desc)+'</div></section><section><h2>Diagnostic énergétique</h2><div class="le-energy"><div><b>DPE</b><strong>'+E(dpe)+'</strong>'+(a.dpe_value?' '+E(a.dpe_value)+' kWh/m²/an':'')+'</div><div><b>GES</b><strong>'+E(ges)+'</strong>'+(a.ghg_value?' '+E(a.ghg_value)+' kg CO₂/m²/an':'')+'</div></div></section>'+(map?'<section><h2>Quartier / localisation</h2><p class="muted">Position approximative</p>'+map+'</section>':'')+'<section><h2>Services</h2><div class="le-services"><div>💳 <b>Crédit immobilier</b><small>Simulation de financement</small><button>Simuler</button></div><div>🏠 <b>Assurance habitation</b><small>Comparer les offres</small><button>Comparer</button></div><div>📋 <b>Diagnostics</b><small>Trouver un professionnel</small><button>Voir</button></div></div></section><footer>Statut : <b>En ligne</b></footer></div></div>'}catch(e){m.innerHTML='<div class="le-bg"><div class="le-sheet"><button class="le-x" onclick="document.getElementById(\'leModal\').remove()">×</button><p class="err">Erreur de chargement</p></div></div>'}}window.openListingDetail=open;const s=document.createElement('style');s.textContent='#leModal{position:fixed;inset:0;z-index:99999}.le-bg{position:absolute;inset:0;background:#0008;display:flex;justify-content:center;align-items:flex-start;padding:18px;overflow:auto}.le-sheet{position:relative;width:min(1000px,100%);max-height:calc(100vh - 36px);overflow:auto;background:#fff;border-radius:20px;padding:22px;box-shadow:0 20px 70px #0006}.le-x{position:absolute;right:14px;top:12px;border:0;border-radius:50%;width:38px;height:38px;font-size:25px}.le-sheet header{display:flex;justify-content:space-between;gap:18px}.le-sheet h1{margin:4px 0 8px}.le-price{font-size:28px}.le-main{width:100%;max-height:480px;object-fit:cover;border-radius:14px;margin-top:12px}.le-th{display:flex;gap:8px;overflow:auto;margin:8px 0}.le-th img{width:82px;height:62px;object-fit:cover;border-radius:8px}.le-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-top:14px}.le-f{padding:12px;border:1px solid #e5e7eb;border-radius:12px;background:#fafafa}.le-f span{display:block;color:#667085;font-size:12px;margin-bottom:4px}.le-chips{display:flex;flex-wrap:wrap;gap:8px}.le-chips span{padding:8px 11px;background:#f2f4f7;border-radius:999px}.le-desc{white-space:pre-wrap;line-height:1.7}.le-energy{display:grid;grid-template-columns:1fr 1fr;gap:10px}.le-energy>div{padding:16px;background:#f5f6f8;border-radius:12px}.le-energy strong{font-size:28px;margin:0 8px}.le-map{width:100%;height:300px;border:0;border-radius:12px}.le-services{display:grid;grid-template-columns:repeat(3,1fr);gap:10px}.le-services>div{border:1px solid #e5e7eb;border-radius:12px;padding:14px}.le-services b,.le-services small{display:block}.le-services button{margin-top:8px}section{margin-top:20px;padding-top:16px;border-top:1px solid #eee}.muted{color:#667085}.err{color:#b42318}footer{margin-top:20px;color:#667085}@media(max-width:700px){.le-grid{grid-template-columns:repeat(2,1fr)}.le-services{grid-template-columns:1fr}.le-sheet header{display:block}.le-price{display:block;margin-top:10px}}';document.head.appendChild(s)})();</script>'''
    page=page.replace('</body>',script+'</body>');response.set_data(page)
 except Exception:pass
 return response
