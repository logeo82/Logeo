import os, json, urllib.parse, urllib.request, statistics
from flask import jsonify
import app as logeo
BASE='https://cherchertrouver.immo/api/v1'
@logeo.app.get('/api/owner/market-reference/<int:listing_id>')
def market_reference(listing_id):
 u=logeo.require_role('owner')
 if not u:return jsonify(error='Connexion propriétaire requise'),401
 c=logeo.db();row=c.execute(logeo.ph('SELECT * FROM listings WHERE id=? AND owner_id=?'),(listing_id,u['id'])).fetchone();c.close()
 if not row:return jsonify(error='Annonce introuvable'),404
 key=os.environ.get('CHERCHER_TROUVER_API_KEY','').strip()
 if not key:return jsonify(ok=False)
 q={'ville':row['city'],'type':row['type'],'transaction':'vente' if row['listing_kind']=='sale' else 'location','page_size':'25'}
 qs=urllib.parse.urlencode(q);req=urllib.request.Request(BASE+'/annonces?'+qs,headers={'X-Api-Key':key,'Accept':'application/json','User-Agent':'LOGEO/1.0'})
 try:
  with urllib.request.urlopen(req,timeout=15) as r:data=json.loads(r.read().decode('utf-8'))
  vals=[float(x['price_per_m2']) for x in data.get('items',[]) if x.get('price_per_m2') not in (None,'')]
  if not vals:
   vals=[float(x['price'])/float(x['surface']) for x in data.get('items',[]) if x.get('price') and x.get('surface')]
  return jsonify(ok=True,city=row['city'],count=len(vals),median=round(statistics.median(vals)),average=round(statistics.mean(vals)) if vals else None,unit='€/m²')
 except Exception as e:return jsonify(ok=False,error=str(e))
@logeo.app.after_request
def inject_market_reference(response):
 try:
  if response.content_type and response.content_type.startswith('text/html'):
   page=response.get_data(as_text=True)
   if 'id="marketReferencePatch"' not in page and 'id="ownerApp"' in page:
    script='''<script id="marketReferencePatch">(function(){function p(){if(typeof window.openListingDetail!=="function")return setTimeout(p,300);if(window.openListingDetail.__ref)return;var old=window.openListingDetail;async function open(id){await old(id);try{var r=await fetch('/api/owner/market-reference/'+id),x=await r.json();if(!x.ok||!x.median)return;var s=document.querySelector('#leModal .le-sheet section');if(!s)return;var e=document.createElement('section');e.innerHTML='<h2>📊 Référence de prix du secteur</h2><div class="le-f"><span>Prix médian observé à '+String(x.city).replace(/</g,'&lt;')+'</span><b>'+x.median+' €/m²</b></div><small class="muted">Calcul indicatif sur '+x.count+' annonces du catalogue Chercher-Trouver.</small>';s.parentNode.insertBefore(e,s)}catch(e){}}open.__ref=true;window.openListingDetail=open}p()})();</script>'''
    page=page.replace('</body>',script+'</body>');response.set_data(page)
 except Exception:pass
 return response
