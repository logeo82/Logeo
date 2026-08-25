(function(){
function addImportBox(){
 const owner=document.getElementById('ownerApp');
 if(!owner || document.getElementById('logeoImportBox')) return;
 const box=document.createElement('div'); box.id='logeoImportBox'; box.className='card'; box.style.cssText='border:2px dashed #8aa4ff;background:#f8faff';
 box.innerHTML='<h3>🔗 Importer une annonce depuis un site immobilier</h3><p class="muted">Colle le lien public d’une annonce Bien’ici, SeLoger, Leboncoin ou autre site compatible.</p><div style="display:flex;gap:8px;flex-wrap:wrap"><input id="logeoImportUrl" type="url" placeholder="https://www.bienici.com/annonce/..." style="flex:1;min-width:240px"><button id="logeoImportBtn">📥 Importer l’annonce</button></div><p id="logeoImportMsg"></p>';
 const form=owner.querySelector('.card'); if(form) form.parentNode.insertBefore(box,form); else owner.prepend(box);
 document.getElementById('logeoImportBtn').onclick=async function(){const url=document.getElementById('logeoImportUrl').value.trim(),msg=document.getElementById('logeoImportMsg');if(!url){msg.textContent='Colle le lien de l’annonce.';msg.className='err';return}msg.textContent='Récupération des informations…';msg.className='muted';try{const r=await fetch('/api/import-url',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({url})}),x=await r.json();if(!r.ok)throw Error(x.error||'Import impossible');msg.textContent=x.duplicate?'Cette annonce est déjà dans LOGEO.':'✅ Annonce importée dans tes annonces !';msg.className='ok';document.getElementById('logeoImportUrl').value='';if(typeof loadOwner==='function')await loadOwner()}catch(e){msg.textContent='❌ '+e.message;msg.className='err'}};
}
function boot(){addImportBox();setTimeout(addImportBox,500);setTimeout(addImportBox,1500)}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',boot);else boot();window.addEventListener('load',boot);
})();
