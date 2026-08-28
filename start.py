import os, json, urllib.parse, urllib.request
from flask import Response, request, jsonify
import app as logeo
from app import app

for _module in ("owner_import","advanced_import","owner_extended","listing_route","seloger_import_v2","market_search","market_import","enrich_endpoint_fix","listing_enrichment","listing_local_parse","market_reference_ui","market_entry","owner_dashboard","student_ui","student_search","bridge_import"):
    try:
        __import__(_module)
        print(f"LOGEO module loaded: {_module}")
    except Exception as exc:
        print(f"LOGEO module disabled: {_module}: {exc}")

def _ct_owner():
    u=logeo.user()
    return u if u and u.get('role')=='owner' else None

def _ct_api(path, params):
    key=os.environ.get('CHERCHER_TROUVER_API_KEY','').strip()
    if not key: raise RuntimeError('CHERCHER_TROUVER_API_KEY absente dans Railway')
    q=urllib.parse.urlencode({k:v for k,v in params.items() if v not in (None,'')}, doseq=True)
    req=urllib.request.Request('https://cherchertrouver.immo/api/v1'+path+('?' + q if q else ''),headers={'X-Api-Key':key,'Accept':'application/json','User-Agent':'LOGEO/1.0'})
    with urllib.request.urlopen(req,timeout=20) as r:return json.loads(r.read().decode('utf-8'))

@app.get('/owner/market')
def definitive_owner_market():
    if not _ct_owner(): return Response('Accès propriétaire requis',status=403,mimetype='text/plain')
    return Response('''<!doctype html><html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>LOGEO — Chercher-Trouver</title><style>body{font-family:system-ui;margin:0;background:#f4f6fa;color:#172033}main{max-width:1100px;margin:auto;padding:18px}.card{background:#fff;border-radius:16px;padding:18px;margin-bottom:14px;box-shadow:0 4px 18px #0001}.grid{display:grid;grid-template-columns:2fr 1fr 1fr 1fr;gap:10px}input,select{width:100%;box-sizing:border-box;padding:11px;border:1px solid #d6dbe5;border-radius:10px;font:inherit}button{border:0;border-radius:10px;padding:11px 16px;background:#111827;color:#fff;font-weight:800;cursor:pointer;margin-top:10px}.item{display:flex;gap:14px;border-top:1px solid #eee;padding:15px 0}.item img{width:180px;height:125px;object-fit:cover;border-radius:10px;background:#eef2f6}.muted{color:#667085}.err{color:#b42318}@media(max-width:700px){.grid{grid-template-columns:1fr}.item{flex-direction:column}.item img{width:100%;height:190px}}a{color:inherit}</style></head><body><main><div class="card"><a href="/">← Retour à LOGEO</a><h1>🔎 Chercher-Trouver</h1><p class="muted">Recherche automatique des annonces multi-portails.</p><div class="grid"><label>Ville<input id="ville" value="Montauban" placeholder="Montauban"></label><label>Transaction<select id="transaction"><option value="">Toutes</option><option value="vente">Vente</option><option value="location">Location</option></select></label><label>Type<select id="type"><option value="">Tous</option><option value="Appartement">Appartement</option><option value="Maison">Maison</option><option value="Terrain">Terrain</option></select></label><label>Prix max<input id="prix_max" type="number"></label></div><button id="search">🔎 Rechercher toutes les annonces</button><p id="msg" class="muted"></p></div><div id="results" class="card"></div></main><script>const E=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));const U=v=>String(v||'').replace(/&/g,'&amp;').replace(/"/g,'&quot;');let items=[];async function search(){let b=document.getElementById('search'),m=document.getElementById('msg'),r=document.getElementById('results');b.disabled=true;m.textContent='Recherche en cours…';try{let p=new URLSearchParams({ville:document.getElementById('ville').value.trim(),transaction:document.getElementById('transaction').value,type:document.getElementById('type').value,prix_max:document.getElementById('prix_max').value,page_size:'25'});let z=await fetch('/api/ct-direct?'+p),x=await z.json();if(!z.ok)throw Error(x.error||'Recherche impossible');items=x.items||[];m.textContent=(x.total??items.length)+' annonce(s) trouvée(s)';r.innerHTML=items.map((a,i)=>{let im=Array.isArray(a.images)&&a.images[0];return '<div class="item">'+(im?'<img src="'+U(im)+'">':'<div style="width:180px;height:125px;background:#eef2f6;border-radius:10px"></div>')+'<div><h2 style="margin:0 0 5px">'+E(a.title||'Annonce')+'</h2><b>'+E(a.price??'Prix NC')+' €</b> · '+E(a.surface??'')+' m² · '+E(a.rooms??'')+' pièce(s)<br><span class="muted">📍 '+E(a.city||'')+' · '+E(a.source||'')+'</span><br><button onclick="imp('+i+')">📥 Importer dans LOGEO</button></div></div>'}).join('')||'<p class="muted">Aucune annonce trouvée.</p>'}catch(e){m.textContent='❌ '+e.message;m.className='err'}finally{b.disabled=false}}async function imp(i){let a=items[i],r=await fetch('/api/market-import',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({source:a.source,reference:a.reference,listing:a})}),x=await r.json();alert(r.ok?(x.duplicate?'Annonce déjà présente dans LOGEO.':'Annonce importée dans LOGEO !'):(x.error||'Import impossible'))}document.getElementById('search').onclick=search;</script></body></html>''',mimetype='text/html')

@app.get('/api/ct-direct')
def definitive_ct_search():
    if not _ct_owner(): return jsonify(error='Connexion propriétaire requise'),403
    try:
        a=request.args;p={k:a.get(k) for k in ('q','type','transaction','ville','cp','dept','region','prix_min','prix_max','surface_min','surface_max','pieces_min','chambres_min','dpe','ges','sort')};p['page_size']=min(int(a.get('page_size','25') or 25),25);data=_ct_api('/annonces',p);items=data.get('items',[]) if isinstance(data,dict) else [];return jsonify(ok=True,total=data.get('total',len(items)),items=items,next_cursor=data.get('next_cursor'),has_more=data.get('has_more',False))
    except Exception as e:return jsonify(error=f'Recherche multi-portails indisponible : {e}'),502

@app.after_request
def definitive_market_entry(response):
    try:
        if response.content_type and response.content_type.startswith('text/html'):
            html=response.get_data(as_text=True)
            if 'id="marketSearchDefinitive"' not in html:
                block='<div id="marketSearchDefinitive" style="margin:12px 0;padding:16px;border:2px solid #111827;border-radius:14px;background:#eef2ff"><div style="font-size:19px;font-weight:800">🔎 Chercher-Trouver</div><div style="color:#667085;margin:5px 0 10px">Recherche automatique multi-portails et import des annonces dans LOGEO.</div><a href="/owner/market" style="display:block;text-decoration:none"><button type="button" style="width:100%;padding:13px;border:0;border-radius:10px;background:#111827;color:#fff;font-weight:800">🔎 Rechercher des annonces</button></a></div>'
                marker='<section id="ownerApp" class="hidden">'
                if marker in html:html=html.replace(marker,marker+block,1)
                response.headers['Cache-Control']='no-store, no-cache, must-revalidate, max-age=0';response.headers['Pragma']='no-cache';response.set_data(html)
    except Exception as exc:print(f'LOGEO market UI injection error: {exc}')
    return response

from waitress import serve
serve(app,host='0.0.0.0',port=int(os.environ.get('PORT','8080')))
