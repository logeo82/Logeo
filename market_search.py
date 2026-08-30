import os, urllib.parse, urllib.request, json, time
from flask import jsonify, Response, request
import app as logeo
BASE='https://cherchertrouver.immo/api/v1'; _CACHE={}; _CACHE_TTL=300
def _api(path,params=None):
 key=os.environ.get('CHERCHER_TROUVER_API_KEY','').strip()
 if not key: raise RuntimeError('CHERCHER_TROUVER_API_KEY absente dans Railway')
 q=urllib.parse.urlencode({k:v for k,v in (params or {}).items() if v not in (None,'')},doseq=True)
 req=urllib.request.Request(BASE+path+('?' + q if q else ''),headers={'X-Api-Key':key,'Accept':'application/json','User-Agent':'LOGEO/1.0'})
 with urllib.request.urlopen(req,timeout=15) as r:return json.loads(r.read().decode())
def _owner():
 u=logeo.user();return bool(u and u.get('role')=='owner')
def _key(s,r):return f'{s}|{r}'
def _remember(items):
 for x in items or []:
  if isinstance(x,dict) and x.get('source') and x.get('reference'):_CACHE[_key(x['source'],x['reference'])]=(time.time(),x)
def _cached(s,r):
 x=_CACHE.get(_key(s,r));return x[1] if x and time.time()-x[0]<_CACHE_TTL else None
@logeo.app.get('/api/market-search')
def market_search():
 if not _owner():return jsonify(error='Connexion propriétaire requise'),403
 try:
  a=request.args;p={k:a.get(k) for k in ('q','type','transaction','ville','cp','dept','region','prix_min','prix_max','surface_min','surface_max','pieces_min','chambres_min','dpe','ges','sort')};p['page_size']=min(int(a.get('page_size','10') or 10),25);d=_api('/annonces',p);items=d.get('items',[]) if isinstance(d,dict) else [];_remember(items);return jsonify(ok=True,total=d.get('total',len(items)),items=items,next_cursor=d.get('next_cursor'),has_more=d.get('has_more',False))
 except Exception as e:return jsonify(error=f'Recherche multi-portails indisponible : {e}'),502
@logeo.app.get('/api/market-detail/<source>/<reference>')
def market_detail(source,reference):
 if not _owner():return jsonify(error='Connexion propriétaire requise'),403
 item=_cached(source,reference)
 if not item:return jsonify(ok=False,error='Annonce absente du cache. Relance la recherche.'),404
 try:
  d=_api('/annonces/'+urllib.parse.quote(str(source),safe='')+'/'+urllib.parse.quote(str(reference),safe=''))
  candidate=d.get('annonce') if isinstance(d,dict) and isinstance(d.get('annonce'),dict) else d.get('item') if isinstance(d,dict) and isinstance(d.get('item'),dict) else d
  if isinstance(candidate,dict):item={**item,**candidate}
  _CACHE[_key(source,reference)]=(time.time(),item);return jsonify(ok=True,annonce=item,cached=False)
 except Exception as e:return jsonify(ok=False,error=f'Détail Chercher-Trouver indisponible : {e}',annonce=item),502
@logeo.app.get('/api/market-ping')
def market_ping():
 if not _owner():return jsonify(error='Connexion propriétaire requise'),403
 try:return jsonify(ok=True,data=_api('/ping'))
 except Exception as e:return jsonify(ok=False,error=str(e)),502
@logeo.app.get('/owner/market')
def owner_market_page():
 if not _owner():return Response('Accès propriétaire requis',403)
 return Response('''<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>LOGEO — Chercher-Trouver</title><style>body{font-family:system-ui;background:#f4f6fa;margin:0;padding:18px}main{max-width:1000px;margin:auto}.card{background:white;padding:18px;border-radius:16px;margin-bottom:14px}input,select{padding:11px;border-radius:10px;border:1px solid #ddd;width:100%;box-sizing:border-box}button{padding:11px 15px;margin-top:8px;border:0;border-radius:10px;background:#111827;color:white;font-weight:700}.item{padding:14px 0;border-top:1px solid #eee}.err{color:#b42318}.muted{color:#667085}</style><main><div class="card"><a href="/">← Retour à LOGEO</a><h1>🔎 Chercher-Trouver</h1><p class="muted">Recherche multi-portails</p><input id="ville" value="Montauban" placeholder="Ville"><button id="go">Rechercher</button><p id="msg" class="muted"></p><div id="results"></div></div><div id="detail"></div></main><script>const E=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));let items=[];async function openA(a){let d=document.getElementById('detail');d.innerHTML='<div class="card">⏳ Récupération du détail…</div>';let r=await fetch('/api/market-detail/'+encodeURIComponent(a.source)+'/'+encodeURIComponent(a.reference)),x=await r.json();if(!r.ok)throw Error(x.error);let z=x.annonce||a,desc=z.description||'';d.innerHTML='<div class="card"><h2>'+E(z.title||'Annonce')+'</h2><b>'+E(z.price||'')+' €</b> · '+E(z.surface||'')+' m²<h3>Description ('+desc.length+' caractères)</h3><p style="white-space:pre-wrap">'+E(desc)+'</p></div>'}document.getElementById('go').onclick=async()=>{let m=document.getElementById('msg'),r=document.getElementById('results');m.textContent='Recherche…';try{let x=await (await fetch('/api/market-search?ville='+encodeURIComponent(ville.value)+'&page_size=20')).json();if(x.error)throw Error(x.error);items=x.items||[];m.textContent=(x.total??items.length)+' annonce(s) trouvée(s)';r.innerHTML=items.map((a,i)=>'<div class="item"><b>'+E(a.title||'Annonce')+'</b><br>'+E(a.price||'')+' € · '+E(a.surface||'')+' m² · '+E(a.city||'')+'<br><button onclick="openA(items['+i+'])">👁 Ouvrir</button></div>').join('')||'Aucune annonce'}catch(e){m.textContent='❌ '+E(e.message);m.className='err'}};</script>''',mimetype='text/html')
