from flask import request
import app as logeo

@logeo.app.after_request
def inject_market_import_buttons(response):
    try:
        if not (response.content_type or '').startswith('text/html') or request.path != '/owner/market':
            return response
        html=response.get_data(as_text=True)
        if 'marketImportUi' in html:
            return response
        script=r'''<script id="marketImportUi">(function(){function install(){const results=document.getElementById('results');if(!results||results.dataset.importUi)return;results.dataset.importUi='1';const obs=new MutationObserver(function(){results.querySelectorAll('.item').forEach(function(item){if(item.querySelector('.market-import-inline'))return;const i=Number(item.dataset.i);if(Number.isNaN(i))return;const b=document.createElement('button');b.className='market-import-inline';b.type='button';b.textContent='📥 Importer dans LOGEO';b.style.cssText='margin-top:8px;width:100%;font-size:15px';b.onclick=async function(ev){ev.stopPropagation();b.disabled=true;b.textContent='⏳ Importation…';try{const ville=(document.getElementById('ville')||{}).value||'';const type=(document.getElementById('type')||{}).value||'';const tx=(document.getElementById('tx')||{}).value||'';const p=new URLSearchParams({ville:ville.trim(),page_size:'20'});if(type)p.set('type',type);if(tx)p.set('transaction',tx);const sr=await fetch('/api/market-search?'+p.toString());const sx=await sr.json();if(!sr.ok)throw Error(sx.error||'Recherche impossible');const a=(sx.items||[])[i];if(!a)throw Error('Annonce introuvable');const ir=await fetch('/api/market-import',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({source:a.source||'',reference:a.reference||''})});const ix=await ir.json();if(!ir.ok)throw Error(ix.error||'Import impossible');b.textContent=ix.duplicate?'⚠️ Déjà importée':'✅ Importée dans LOGEO';}catch(e){b.disabled=false;b.textContent='❌ '+e.message;}};const target=item.querySelector('div:last-child');if(target)target.appendChild(b);});});obs.observe(results,{childList:true,subtree:true});}setInterval(install,300);install();})();</script>'''
        response.set_data(html.replace('</body>',script+'</body>'))
    except Exception:
        pass
    return response
