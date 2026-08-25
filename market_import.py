import json
from flask import jsonify, request
import app as logeo
try:
    import market_import_ui
except Exception as e:
    print('LOGEO market import UI disabled:', e)

def _api_search(reference):
    import market_search
    data = market_search._api('/annonces', {'q': reference, 'page_size': 10})
    items = data.get('items', []) if isinstance(data, dict) else []
    for item in items:
        if str(item.get('reference', '')) == str(reference): return item
    return None

def _photos(item):
    p = item.get('images', [])
    return p if isinstance(p, list) else []

@logeo.app.post('/api/market-import')
def market_import():
    u = logeo.user()
    if not u or u['role'] != 'owner': return jsonify(error='Connexion propriétaire requise'), 403
    x = request.get_json(silent=True) or {}
    source, reference = str(x.get('source') or '').strip(), str(x.get('reference') or '').strip()
    if not source or not reference: return jsonify(error='Annonce multi-portails invalide'), 400
    try:
        item = _api_search(reference)
        if not item: return jsonify(error='Annonce introuvable dans le catalogue ChercherTrouver'), 404
        source = str(item.get('source') or source); external = item.get('external_url')
        if not external:
            for s in (item.get('sources') or []):
                if s.get('source') == source and s.get('url'): external = s['url']; break
            if not external and item.get('sources'): external = item['sources'][0].get('url')
        c = logeo.db()
        try:
            try: c.execute("ALTER TABLE listings ADD COLUMN photos TEXT DEFAULT '[]'")
            except Exception: pass
            existing = c.execute('SELECT * FROM listings WHERE source_url=?', (external,)).fetchone() if external else None
            if existing: return jsonify(ok=True, duplicate=True, id=existing['id'], listing=dict(existing))
        finally: c.close()
        import owner_extended
        payload = {'listing_kind':'sale' if item.get('transaction_type') == 'vente' else 'location','title':item.get('title') or 'Annonce immobilière','city':item.get('city') or '','postal_code':item.get('postal_code'),'price':item.get('price') or 0,'surface':item.get('surface') or 0,'type':item.get('type') or 'Appartement','rooms':item.get('rooms'),'bedrooms':item.get('bedrooms'),'bathrooms':item.get('bathrooms'),'parking':item.get('parking'),'parking_interior':item.get('parking_interior'),'parking_exterior':item.get('parking_exterior'),'cellar':item.get('cellar'),'garden':item.get('garden'),'elevator':item.get('elevator'),'balcony':item.get('balcony'),'dpe_class':item.get('dpe'),'dpe_value':item.get('dpe_value'),'ghg_class':item.get('ges'),'ghg_value':item.get('ges_value'),'description':item.get('description') or '','photos':_photos(item)[:30],'source':source,'source_url':external,'furnished':item.get('furnished',False)}
        return owner_extended._insert(payload, u)
    except Exception as e: return jsonify(error=f'Import ChercherTrouver impossible : {type(e).__name__}: {e}'), 500

@logeo.app.after_request
def market_import_ui(response):
    try:
        if response.content_type and response.content_type.startswith('text/html') and '/owner/market' in (request.path or ''):
            page=response.get_data(as_text=True)
            if 'marketImportScript' not in page:
                script='''<script id="marketImportScript">(function(){function install(){const r=document.getElementById('results');if(!r||r.dataset.mi)return;r.dataset.mi='1';r.querySelectorAll('.item').forEach(function(item){if(item.querySelector('.mi'))return;const i=Number(item.dataset.i);const b=document.createElement('button');b.className='mi';b.type='button';b.textContent='📥 Importer dans LOGEO';b.style.cssText='margin-top:8px;width:100%;font-size:15px';b.onclick=async function(e){e.stopPropagation();b.disabled=true;b.textContent='⏳ Importation…';try{const p=new URLSearchParams({ville:(document.getElementById('ville')||{}).value||'',page_size:'20'});const t=(document.getElementById('type')||{}).value;if(t)p.set('type',t);const tx=(document.getElementById('tx')||{}).value;if(tx)p.set('transaction',tx);const sr=await fetch('/api/market-search?'+p);const sx=await sr.json();const a=(sx.items||[])[i];if(!a)throw Error('Annonce introuvable');const ir=await fetch('/api/market-import',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({source:a.source||'',reference:a.reference||''})});const ix=await ir.json();if(!ir.ok)throw Error(ix.error||'Import impossible');b.textContent=ix.duplicate?'⚠️ Déjà importée':'✅ Importée dans LOGEO'}catch(x){b.disabled=false;b.textContent='❌ '+x.message}};item.appendChild(b)})}setInterval(install,300);install()})();</script>'''
                response.set_data(page.replace('</body>',script+'</body>'))
    except Exception: pass
    return response
