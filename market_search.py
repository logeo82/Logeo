import os, urllib.parse, urllib.request, json, time
from flask import jsonify, Response, request
import app as logeo

BASE='https://cherchertrouver.immo/api/v1'
_CACHE={}
_CACHE_TTL=300

def _api(path, params=None):
    key=os.environ.get('CHERCHER_TROUVER_API_KEY','').strip()
    if not key: raise RuntimeError('CHERCHER_TROUVER_API_KEY absente dans Railway')
    params=params or {}
    q=urllib.parse.urlencode({k:v for k,v in params.items() if v not in (None,'')}, doseq=True)
    req=urllib.request.Request(BASE+path+('?' + q if q else ''),headers={'X-Api-Key':key,'Accept':'application/json','User-Agent':'LOGEO/1.0'},method='GET')
    with urllib.request.urlopen(req,timeout=15) as r:
        return json.loads(r.read().decode('utf-8'))

def _cache_key(source, reference): return f'{source}|{reference}'
def _remember(items):
    now=time.time()
    for item in items or []:
        if isinstance(item,dict) and item.get('source') and item.get('reference'):
            _CACHE[_cache_key(item['source'],item['reference'])]=(now,item)
    for k,(t,_) in list(_CACHE.items()):
        if now-t>_CACHE_TTL: _CACHE.pop(k,None)

def cached_listing(source, reference):
    v=_CACHE.get(_cache_key(source,reference))
    if not v:return None
    if time.time()-v[0]>_CACHE_TTL:
        _CACHE.pop(_cache_key(source,reference),None);return None
    return v[1]

@logeo.app.get('/api/market-search')
def market_search():
    u=logeo.user()
    if not u or u['role']!='owner': return jsonify(error='Connexion propriétaire requise'),403
    try:
        args=logeo.request.args
        p={k:args.get(k) for k in ('q','type','transaction','ville','cp','dept','region','prix_min','prix_max','surface_min','surface_max','pieces_min','chambres_min','dpe','ges','sort')}
        p['page_size']=min(int(args.get('page_size','10') or 10),25)
        data=_api('/annonces',p)
        items=data.get('items',[]) if isinstance(data,dict) else []
        _remember(items)
        return jsonify(ok=True,total=data.get('total',len(items)),items=items,next_cursor=data.get('next_cursor'),has_more=data.get('has_more',False))
    except Exception as e:
        return jsonify(error=f'Recherche multi-portails indisponible : {e}'),502

@logeo.app.get('/api/market-detail/<source>/<reference>')
def market_detail(source,reference):
    u=logeo.user()
    if not u or u['role']!='owner': return jsonify(error='Connexion propriétaire requise'),403
    item=cached_listing(source,reference)
    if not item:return jsonify(ok=False,error='Annonce non disponible dans le résultat de recherche. Relance la recherche.'),404
    return jsonify(ok=True,annonce=item,cached=True)

@logeo.app.get('/api/market-ping')
def market_ping():
    u=logeo.user()
    if not u or u['role']!='owner': return jsonify(error='Connexion propriétaire requise'),403
    try:return jsonify(ok=True,data=_api('/ping'))
    except Exception as e:return jsonify(ok=False,error=str(e)),502

@logeo.app.get('/owner/market')
def owner_market_page():
    u=logeo.user()
    if not u or u['role']!='owner': return Response('Accès propriétaire requis',status=403,mimetype='text/plain')
    return Response('''<!doctype html><html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>LOGEO — Recherche multi-portails</title><style>body{font-family:system-ui;background:#f4f6fa;color:#172033;margin:0}main{max-width:1000px;margin:auto;padding:18px}.card{background:#fff;padding:18px;border-radius:16px;margin:12px 0;box-shadow:0 4px 18px #0001}input,select{padding:11px;border:1px solid #d6dbe5;border-radius:10px;font:inherit;width:100%;box-sizing:border-box}button{padding:11px 15px;border:0;border-radius:10px;background:#111827;color:white;font-weight:700;margin-top:8px;cursor:pointer}.grid{display:grid;grid-template-columns:2fr 1fr 1fr;gap:10px}@media(max-width:650px){.grid{grid-template-columns:1fr}.item{flex-direction:column}.item img{width:100%!important;height:180px!important}}.muted{color:#667085}.err{color:#b42318}.item{display:flex;gap:14px;border-top:1px solid #eee;padding:14px 0;cursor:pointer}.item img{width:150px;height:110px;object-fit:cover;border-radius:10px;background:#eef2f6}.detail img{width:180px;height:130px;object-fit:cover;border-radius:10px;margin:5px}.actions{display:flex;gap:8px;flex-wrap:wrap}.publish{background:#067647!important}</style></head><body><main><div class="card"><a href="/" style="text-decoration:none">← Retour à LOGEO</a><h1>🌐 Recherche multi-portails</h1><p class="muted">Annonces agrégées depuis plusieurs portails et réseaux immobiliers.</p><div class="grid"><label>Ville<input id="ville" value="Montauban" placeholder="Montauban"></label><label>Type<select id="type"><option value="">Tous</option><option value="Appartement">Appartement</option><option value="Maison">Maison</option><option value="Terrain">Terrain</option></select></label><label>Transaction<select id="tx"><option value="">Toutes</option><option value="vente">Vente</option><option value="location">Location</option></select></label></div><button id="go">🔎 Rechercher</button><p id="msg" class="muted"></p><div id="results"></div></div><div id="detail"></div></main><script>const esc=v=>String(v??'').replace(/[&<>\\"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','\\"':'&quot;',"'":'&#39;'}[c]));const url=v=>String(v||'').replace(/&/g,'&amp;').replace(/\\"/g,'&quot;');let currentItems=[];async function openDetail(a){const d=document.getElementById('detail');const imgs=Array.isArray(a.images)?a.images:[];d.innerHTML='<div class="card detail"><h2>'+esc(a.title||'Annonce')+'</h2><h3>'+esc(a.price??'')+' € · '+esc(a.surface??'')+' m² · '+esc(a.rooms??'')+' pièce(s)</h3><p>📍 '+esc(a.city||'')+' '+esc(a.postal_code||'')+'<br>🏢 '+esc(a.real_estate_network||a.seller_name||a.source||'')+'<br>⚡ DPE '+esc(a.dpe||'')+' · GES '+esc(a.ges||'')+'</p><div>'+imgs.map(i=>'<img src="'+url(i)+'" loading="lazy">').join('')+'</div><p style="white-space:pre-wrap">'+esc(a.description||'')+'</p><div class="actions">'+(a.external_url?'<a href="'+url(a.external_url)+'" target="_blank" rel="noopener"><button type="button">🔗 Annonce originale</button></a>':'')+'<button class="publish" id="publishBtn" type="button">📢 Diffuser sur LOGEO</button></div><p id="publishMsg" class="muted"></p></div>';d.scrollIntoView({behavior:'smooth'});document.getElementById('publishBtn').onclick=()=>publish(a)}async function publish(a){const b=document.getElementById('publishBtn'),m=document.getElementById('publishMsg');b.disabled=true;b.textContent='⏳ Publication…';try{const r=await fetch('/api/market-import',{method:'POST',headers:{'Content-Type':'application/json','Accept':'application/json'},body:JSON.stringify({source:a.source,reference:a.reference,listing:a})});const x=await r.json();if(!r.ok)throw Error(x.error||'Publication impossible');m.textContent=x.duplicate?'⚠️ Cette annonce existe déjà dans LOGEO.':'✅ Annonce diffusée dans LOGEO.';m.className=x.duplicate?'muted':'ok'}catch(e){m.textContent='❌ '+e.message;m.className='err'}finally{b.disabled=false;b.textContent='📢 Diffuser sur LOGEO'}}document.getElementById('go').onclick=async()=>{const b=document.getElementById('go'),m=document.getElementById('msg'),r=document.getElementById('results');b.disabled=true;m.textContent='Recherche…';r.innerHTML='';document.getElementById('detail').innerHTML='';try{const q=new URLSearchParams({ville:document.getElementById('ville').value.trim(),page_size:'20'});if(document.getElementById('type').value)q.set('type',document.getElementById('type').value);if(document.getElementById('tx').value)q.set('transaction',document.getElementById('tx').value);const x=await fetch('/api/market-search?'+q),data=await x.json();if(!x.ok)throw Error(data.error||'Recherche impossible');currentItems=data.items||[];m.textContent=(data.total??currentItems.length)+' annonce(s) trouvée(s).';r.innerHTML=currentItems.map((a,i)=>{const img=Array.isArray(a.images)&&a.images.length?a.images[0]:'';return '<div class="item" data-i="'+i+'">'+(img?'<img src="'+url(img)+'">':'<div style="width:150px;height:110px;border-radius:10px;background:#eef2f6"></div>')+'<div style="flex:1"><h2 style="margin:0 0 6px">'+esc(a.title||'Annonce')+'</h2><b>'+esc(a.price??'')+' €</b> · '+esc(a.surface??'')+' m² · '+esc(a.rooms||'')+' pièce(s)<br><span class="muted">📍 '+esc(a.city||'')+' · 🏢 '+esc(a.real_estate_network||a.seller_name||a.source||'')+' · 📷 '+esc(a.images_count||a.images?.length||0)+' photo(s)</span><div class="actions"><button type="button" class="openBtn">👁 Ouvrir dans LOGEO</button><button type="button" class="publish publishBtn">📢 Diffuser sur LOGEO</button></div></div></div>'}).join('')||'<p class="muted">Aucune annonce trouvée.</p>';r.querySelectorAll('.item').forEach(el=>{const a=currentItems[Number(el.dataset.i)];el.querySelector('.openBtn').onclick=e=>{e.stopPropagation();openDetail(a)};el.querySelector('.publishBtn').onclick=e=>{e.stopPropagation();openDetail(a).then(()=>publish(a))}})}catch(e){m.textContent='❌ '+e.message;m.className='err'}finally{b.disabled=false}};</script></body></html>''',mimetype='text/html')

@logeo.app.after_request
def inject_market_search(response):
    try:
        if response.content_type and response.content_type.startswith('text/html'):
            html=response.get_data(as_text=True)
            if 'id="ownerApp"' in html and '🌐 Rechercher des annonces' not in html:
                button='<div id="marketSearchEntry" style="margin:12px 0"><a href="/owner/market" style="display:block;text-decoration:none"><button type="button" style="width:100%;font-size:16px">🌐 Rechercher des annonces multi-portails</button></a></div>'
                marker='<section id="ownerApp" class="hidden">'
                if marker in html:html=html.replace(marker,marker+button,1)
                response.set_data(html)
    except Exception:pass
    return response
