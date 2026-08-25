from flask import request
import app as logeo

@logeo.app.after_request
def force_owner_import_ui(response):
    try:
        if response.content_type and response.content_type.startswith('text/html'):
            page = response.get_data(as_text=True)
            if 'id="ownerApp"' in page and 'id="ownerImportBox"' not in page:
                block = '''<div id="ownerImportBox" class="card" style="border:2px solid #111827;margin-bottom:16px"><h3>🔗 Importer une annonce</h3><p class="muted">Colle le lien d'une annonce immobilière (SeLoger, Bien'ici, etc.).</p><div style="display:flex;gap:8px;flex-wrap:wrap"><input id="ownerImportUrl" type="url" placeholder="https://..." style="flex:1;min-width:220px"><button id="ownerImportBtn" type="button">📥 Importer l'annonce</button></div><p id="ownerImportMsg"></p></div><script>(function(){function init(){var b=document.getElementById('ownerImportBtn');if(!b||b.dataset.ready)return;b.dataset.ready='1';b.onclick=async function(){var input=document.getElementById('ownerImportUrl'),msg=document.getElementById('ownerImportMsg'),url=input.value.trim();if(!url){msg.textContent='❌ Colle le lien de l’annonce.';msg.className='err';return}b.disabled=true;b.textContent='⏳ Import…';msg.textContent='Récupération des informations…';try{var r=await fetch('/api/import-url',{method:'POST',headers:{'Content-Type':'application/json','Accept':'application/json'},body:JSON.stringify({url:url})});var raw=await r.text(),x;try{x=JSON.parse(raw)}catch(e){throw Error('Réponse serveur invalide (HTTP '+r.status+').')};if(!r.ok)throw Error(x.error||'Import impossible');msg.textContent=x.duplicate?'⚠️ Cette annonce est déjà importée.':'✅ Annonce importée !';msg.className='ok';input.value='';if(typeof loadOwner==='function')loadOwner()}catch(e){msg.textContent='❌ '+e.message;msg.className='err'}finally{b.disabled=false;b.textContent='📥 Importer l\'annonce'}}}if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init);else init()})();</script>'''
                pos = page.find('>', page.find('<section id="ownerApp"'))
                if pos >= 0:
                    page = page[:pos+1] + block + page[pos+1:]
                    response.set_data(page)
    except Exception:
        pass
    return response
