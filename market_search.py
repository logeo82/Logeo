import os, urllib.parse, urllib.request, json
from flask import jsonify, Response
import app as logeo

BASE='https://cherchertrouver.immo/api/v1'

def _api(path, params):
    key=os.environ.get('CHERCHER_TROUVER_API_KEY','').strip()
    if not key: raise RuntimeError('CHERCHER_TROUVER_API_KEY absente dans Railway')
    q=urllib.parse.urlencode({k:v for k,v in params.items() if v not in (None,'')})
    req=urllib.request.Request(BASE+path+('?' + q if q else ''),headers={'X-Api-Key':key,'Accept':'application/json','User-Agent':'LOGEO/1.0'},method='GET')
    with urllib.request.urlopen(req,timeout=15) as r:
        return json.loads(r.read().decode('utf-8')), {'from':r.headers.get('X-Annonces-From'),'used':r.headers.get('X-Quota-Items-Used'),'limit':r.headers.get('X-Quota-Items-Limit')}

@logeo.app.get('/api/market-search')
def market_search():
    u=logeo.user()
    if not u or u['role']!='owner':return jsonify(error='Connexion propriétaire requise'),403
    try:
        args=logeo.request.args;city=(args.get('ville') or '').strip()
        p={k:args.get(k) for k in ('q','type','transaction','ville','cp','dept','region','prix_min','prix_max','surface_min','surface_max','pieces_min','chambres_min','dpe','ges','sort')}
        p['page_size']=min(int(args.get('page_size','10') or 10),25)
        data,meta=_api('/annonces',p);items=data.get('items',[]) if isinstance(data,dict) else [];fallback=False
        if not items and city:
            p2=dict(p);p2.pop('ville',None);p2['q']=city
            data2,meta2=_api('/annonces',p2);items=data2.get('items',[]) if isinstance(data2,dict) else []
            if items:data,meta,fallback=data2,meta2,True
        return jsonify(ok=True,total=data.get('total',len(items)),items=items,next_cursor=data.get('next_cursor'),has_more=data.get('has_more',False),fallback=fallback,meta=meta)
    except Exception as e:return jsonify(error=f'Recherche multi-portails indisponible : {e}'),502

@logeo.app.get('/api/market-ping')
def market_ping():
    u=logeo.user()
    if not u or u['role']!='owner': return jsonify(error='Connexion propriétaire requise'),403
    try:
        data,meta=_api('/ping',{});return jsonify(ok=True,data=data,meta=meta)
    except Exception as e:return jsonify(ok=False,error=str(e)),502

@logeo.app.get('/owner/market')
def owner_market_page():
    u=logeo.user()
    if not u or u['role']!='owner': return Response('Accès propriétaire requis',status=403,mimetype='text/plain')
    return Response('''<!doctype html><html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>LOGEO — Recherche multi-portails</title><style>body{font-family:system-ui;background:#f4f6fa;color:#172033;margin:0}main{max-width:1000px;margin:auto;padding:18px}.card{background:#fff;padding:18px;border-radius:16px;margin:12px 0;box-shadow:0 4px 18px #0001}input,select{padding:11px;border:1px solid #d6dbe5;border-radius:10px;font:inherit;width:100%;box-sizing:border-box}button{padding:11px 15px;border:0;border-radius:10px;background:#111827;color:white;font-weight:700;margin-top:8px;cursor:pointer}.grid{display:grid;grid-template-columns:2fr 1fr 1fr;gap:10px}@media(max-width:650px){.grid{grid-template-columns:1fr}.item{flex-direction:column}.item img{width:100%!important;height:180px!important}}.muted{color:#667085}.err{color:#b42318}.ok{color:#087443}.item{display:flex;gap:14px;border-top:1px solid #eee;padding:14px 0}.item img{width:150px;height:110px;object-fit:cover;border-radius:10px;background:#eef2f6}</style></head><body><main><div class="card"><a href="/" style="text-decoration:none">← Retour à LOGEO</a><h1>🌐 Recherche multi-portails</h1><p class="muted">Annonces agrégées depuis plusieurs portails et réseaux immobiliers.</p><div class="grid"><label>Ville<input id="ville" value="Montauban" placeholder="Montauban"></label><label>Type<select id="type"><option value="">Tous</option><option value="Appartement">Appartement</option><option value="Maison">Maison</option><option value="Terrain">Terrain</option></select></label><label>Transaction<select id="tx"><option value="">Toutes</option><option value="vente">Vente</option><option value="location">Location</option></select></label></div><button id="go">🔎 Rechercher</button><p id="msg" class="muted"></p><div id="results"></div></div></main><script>const esc=v=>String(v??'').replace(/[&<>\"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','\"':'&quot;',"'":'&#39;'}[c]));document.getElementById('go').onclick=async()=>{const b=document.getElementById('go'),m=document.getElementById('msg'),r=document.getElementById('results');b.disabled=true;m.textContent='Recherche…';r.innerHTML='';try{const q=new URLSearchParams({ville:document.getElementById('ville').value.trim(),page_size:'20'});if(document.getElementById('type').value)q.set('type',document.getElementById('type').value);if(document.getElementById('tx').value)q.set('transaction',document.getElementById('tx').value);const x=await fetch('/api/market-search?'+q);const d=await x.json();if(!x.ok)throw Error(d.error||'Recherche impossible');m.textContent=(d.total??d.items.length)+' annonce(s) trouvée(s).'+(d.fallback?' Recherche élargie utilisée.':'')+(d.meta?.from?' Catalogue accessible depuis '+d.meta.from+'.':'');r.innerHTML=(d.items||[]).map(a=>{const img=Array.isArray(a.images)&&a.images.length?a.images[0]:'';return '<div class="item">'+(img?'<img src="'+esc(img)+'">':'<div style="width:150px;height:110px;border-radius:10px;background:#eef2f6"></div>')+'<div><h2 style="margin:0 0 6px">'+esc(a.title||'Annonce')+'</h2><b>'+esc(a.price)+' €</b> · '+esc(a.surface)+' m² · '+esc(a.rooms||'')+' pièce(s)<br><span class="muted">📍 '+esc(a.city||'')+' · 🏢 '+esc(a.real_estate_network||a.seller_name||a.source||'')+' · 📷 '+esc(a.images_count||0)+' photo(s)</span><p>'+esc(a.description||'')+'</p></div></div>'}).join('')||'<p class="muted">Aucune annonce trouvée. Si ton compte ChercherTrouver vient d’être créé, son catalogue API commence à la date de création du compte : il peut donc être encore presque vide. La documentation indique qu’un accès historique doit être demandé pour voir les annonces antérieures.</p>'}catch(e){m.textContent='❌ '+e.message;m.className='err'}finally{b.disabled=false}};</script></body></html>''',mimetype='text/html')

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
