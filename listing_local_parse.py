import re, json
from flask import jsonify
import app as logeo

def parse_text(text):
 t=(text or '').replace('\xa0',' ')
 low=t.lower();o={}
 if re.search(r'\brez[ -]?de[ -]?chauss[ée]e?\b|\brdc\b',low):o['floor']='Rez-de-chaussée'
 if re.search(r'\bmeubl[ée]e?\b',low):o['furnished']=1
 if re.search(r'\bpas de balcon\b|\bsans balcon\b',low):o['balcony']=0
 m=re.search(r'(\d+)\s*(?:wc|toilettes?)\b',low)
 if m:o['toilets']=float(m.group(1))
 m=re.search(r'(\d+)\s*(?:salle[s]?\s+d[’\']eau|salle[s]?\s+de\s+douche)',low)
 if m:o['shower_rooms']=float(m.group(1))
 if 'cuisine intégrée' in low or 'cuisine équipée' in low or 'cuisine equipee' in low:o['kitchen']='Intégrée / équipée'
 elif 'cuisine aménagée' in low:o['kitchen']='Aménagée'
 m=re.search(r'classe énergie\s*([a-g])',low)
 if not m:m=re.search(r'classe énergétique\s*([a-g])',low)
 if m:o['dpe_class']=m.group(1).upper()
 m=re.search(r'classe climat\s*([a-g])',low)
 if not m:m=re.search(r'(?:ges|gaz à effet de serre)\s*[:\-]?\s*([a-g])',low)
 if m:o['ghg_class']=m.group(1).upper()
 m=re.search(r'honoraires[^.\n]{0,120}?([0-9][0-9 .]*)\s*€\s*(?:ttc)?',low)
 if m:o['tenant_fees']=float(re.sub(r'[^0-9.]','',m.group(1)).replace(' ','') or 0)
 m=re.search(r'dép[oô]t de garantie\s*([0-9][0-9 .]*)\s*€',low)
 if m:o['deposit']=float(re.sub(r'[^0-9.]','',m.group(1)).replace(' ','') or 0)
 m=re.search(r'(?:charges|provision sur charges)\s*([0-9][0-9 .]*)\s*€\s*/?\s*mois',low)
 if m:o['charges']=float(re.sub(r'[^0-9.]','',m.group(1)).replace(' ','') or 0)
 m=re.search(r'(?:libre|disponible)(?:\s+le)?\s+(\d{1,2}/\d{1,2}/\d{4})',low)
 if m:o['available_date']=m.group(1)
 return o
@logeo.app.post('/api/owner/enrich-local/<int:listing_id>')
def enrich_local(listing_id):
 u=logeo.require_role('owner')
 if not u:return jsonify(error='Connexion propriétaire requise'),401
 c=logeo.db();row=c.execute(logeo.ph('SELECT * FROM listings WHERE id=? AND owner_id=?'),(listing_id,u['id'])).fetchone()
 if not row:c.close();return jsonify(error='Annonce introuvable'),404
 a=dict(row);o=parse_text(a.get('description') or '')
 sets=[];vals=[]
 for k,v in o.items():
  if a.get(k) in (None,'',[]):sets.append(f'{k}={"%s" if logeo.USE_PG else "?"}');vals.append(v)
 feats=[]
 for k,label in [('floor','Étage'),('toilets','WC'),('shower_rooms','Salle de douche'),('kitchen','Cuisine'),('furnished','Meublé'),('balcony','Balcon'),('parking','Parking'),('terrace','Terrasse')]:
  v=o.get(k,a.get(k))
  if v not in (None,''):feats.append(label+(': '+str(v) if k in ('floor','toilets','shower_rooms','kitchen') else (' : Oui' if v in (1,True,'1') else ' : Non')))
 if feats:sets.append(f'listing_features={"%s" if logeo.USE_PG else "?"}');vals.append(json.dumps(feats,ensure_ascii=False))
 if sets:vals.append(listing_id);c.execute('UPDATE listings SET '+','.join(sets)+(' WHERE id=%s' if logeo.USE_PG else ' WHERE id=?'),vals);c.commit()
 row=c.execute(logeo.ph('SELECT * FROM listings WHERE id=?'),(listing_id,)).fetchone();c.close();return jsonify(ok=True,listing=dict(row),derived=o)
@logeo.app.after_request
def patch_existing_detail(response):
 try:
  if response.content_type and response.content_type.startswith('text/html'):
   page=response.get_data(as_text=True)
   if 'id="ownerApp"' in page and 'listingLocalPatch' not in page:
    script='''<script id="listingLocalPatch">(function(){function patch(){if(typeof window.openListingDetail!=="function")return setTimeout(patch,250);if(window.openListingDetail.__local)return;var old=window.openListingDetail;async function open(id){await old(id);try{var r=await fetch("/api/owner/enrich-local/"+id,{method:"POST"}),x=await r.json(),a=x.listing||{};var d=document.querySelector("#leModal .le-desc");if(d)d.textContent=a.description||"Description non disponible";var grid=document.querySelector("#leModal .le-grid");if(grid){var vals=[['Étage',a.floor],['Meublé',a.furnished===1?'Oui':a.furnished===0?'Non':null],['Disponibilité',a.available_date],['WC',a.toilets],['Salle de douche',a.shower_rooms],['Cuisine',a.kitchen],['Honoraires locataire',a.tenant_fees!=null?a.tenant_fees+' € TTC':null],['Charges',a.charges!=null?a.charges+' €/mois':null],['Dépôt de garantie',a.deposit!=null?a.deposit+' €':null],['DPE',a.dpe_class],['GES',a.ghg_class]];vals.forEach(function(v){if(v[1]!==null&&v[1]!==undefined&&v[1]!==''&&!Array.from(grid.children).some(function(e){return e.innerText.indexOf(v[0])>=0})){var e=document.createElement('div');e.className='le-f';e.innerHTML='<span>'+v[0]+'</span><b>'+String(v[1]).replace(/</g,'&lt;')+'</b>';grid.appendChild(e)}})}}catch(e){}}open.__local=true;window.openListingDetail=open}patch()})();</script>'''
    page=page.replace('</body>',script+'</body>');response.set_data(page)
 except Exception:pass
 return response
