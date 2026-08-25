import json
from flask import jsonify, request
import app as logeo


def _api_search(reference):
    import market_search
    data = market_search._api('/annonces', {'q': reference, 'page_size': 10})
    items = data.get('items', []) if isinstance(data, dict) else []
    for item in items:
        if str(item.get('reference', '')) == str(reference):
            return item
    return None


def _photos(item):
    p = item.get('images', [])
    return p if isinstance(p, list) else []


@logeo.app.post('/api/market-import')
def market_import():
    u = logeo.user()
    if not u or u['role'] != 'owner':
        return jsonify(error='Connexion propriétaire requise'), 403
    x = request.get_json(silent=True) or {}
    source = str(x.get('source') or '').strip()
    reference = str(x.get('reference') or '').strip()
    if not source or not reference:
        return jsonify(error='Annonce multi-portails invalide'), 400
    try:
        item = _api_search(reference)
        if not item:
            return jsonify(error='Annonce introuvable dans le catalogue ChercherTrouver'), 404
        source = str(item.get('source') or source)
        external = item.get('external_url')
        if not external:
            sources = item.get('sources') or []
            for s in sources:
                if s.get('source') == source and s.get('url'):
                    external = s['url']; break
            if not external and sources:
                external = sources[0].get('url')
        c = logeo.db()
        try:
            try: c.execute("ALTER TABLE listings ADD COLUMN photos TEXT DEFAULT '[]'")
            except Exception: pass
            existing = c.execute('SELECT * FROM listings WHERE source_url=?', (external,)).fetchone() if external else None
            if existing:
                return jsonify(ok=True, duplicate=True, id=existing['id'], listing=dict(existing))
        finally:
            c.close()
        import owner_extended
        payload = {
            'listing_kind': 'sale' if item.get('transaction_type') == 'vente' else 'location',
            'title': item.get('title') or 'Annonce immobilière', 'city': item.get('city') or '',
            'postal_code': item.get('postal_code'), 'price': item.get('price') or 0,
            'surface': item.get('surface') or 0, 'type': item.get('type') or 'Appartement',
            'rooms': item.get('rooms'), 'bedrooms': item.get('bedrooms'), 'bathrooms': item.get('bathrooms'),
            'parking': item.get('parking'), 'parking_interior': item.get('parking_interior'), 'parking_exterior': item.get('parking_exterior'),
            'cellar': item.get('cellar'), 'garden': item.get('garden'), 'elevator': item.get('elevator'), 'balcony': item.get('balcony'),
            'dpe_class': item.get('dpe'), 'dpe_value': item.get('dpe_value'), 'ghg_class': item.get('ges'), 'ghg_value': item.get('ges_value'),
            'description': item.get('description') or '', 'photos': _photos(item)[:30],
            'source': source, 'source_url': external, 'furnished': item.get('furnished', False)
        }
        return owner_extended._insert(payload, u)
    except Exception as e:
        return jsonify(error=f'Import ChercherTrouver impossible : {type(e).__name__}: {e}'), 500


@logeo.app.after_request
def market_import_ui(response):
    try:
        if response.content_type and response.content_type.startswith('text/html') and '/owner/market' in (request.path or ''):
            page = response.get_data(as_text=True)
            if 'marketImportScript' not in page:
                script = '''<script id="marketImportScript">(function(){let selected=null;async function choose(i){const ville=document.getElementById('ville')?.value.trim()||'';const type=document.getElementById('type')?.value||'';const tx=document.getElementById('tx')?.value||'';const p=new URLSearchParams({ville:ville,page_size:'20'});if(type)p.set('type',type);if(tx)p.set('transaction',tx);try{const r=await fetch('/api/market-search?'+p);const x=await r.json();selected=(x.items||[])[i]||null}catch(e){selected=null}}function addButton(){if(!selected)return;const d=document.getElementById('detail');if(!d||!d.querySelector('.card'))return;if(document.getElementById('marketImportBtn'))return;const b=document.createElement('button');b.id='marketImportBtn';b.type='button';b.textContent='📥 Importer cette annonce dans LOGEO';b.style.cssText='width:100%;font-size:16px;margin-top:14px';b.onclick=async()=>{b.disabled=true;b.textContent='⏳ Importation…';try{const r=await fetch('/api/market-import',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({source:selected.source,reference:selected.reference})});const x=await r.json();if(!r.ok)throw Error(x.error||'Import impossible');b.textContent=x.duplicate?'⚠️ Déjà importée dans LOGEO':'✅ Annonce importée dans LOGEO';}catch(e){b.disabled=false;b.textContent='❌ '+e.message;}};d.querySelector('.card').appendChild(b)}function watch(){const r=document.getElementById('results');if(!r||r.dataset.marketWatch)return;r.dataset.marketWatch='1';r.addEventListener('click',async e=>{const item=e.target.closest('.item');if(!item)return;await choose(Number(item.dataset.i));setTimeout(addButton,100)});new MutationObserver(addButton).observe(document.getElementById('detail')||document.body,{childList:true,subtree:true})}setInterval(watch,300)})();</script>'''
                response.set_data(page.replace('</body>', script + '</body>'))
    except Exception: pass
    return response
'''
