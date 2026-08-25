(function(){
function addOwnerImporter(){
 const section=document.getElementById('ownerApp'); if(!section||document.getElementById('ownerImportBox'))return;
 const box=document.createElement('div'); box.id='ownerImportBox'; box.className='card'; box.innerHTML='<h3>🔗 Importer une annonce depuis une URL</h3><p class="muted">Colle le lien public d’une annonce Bien’ici ou d’un autre site immobilier.</p><div style="display:flex;gap:8px;flex-wrap:wrap"><input id="ownerImportUrl" placeholder="https://www.bienici.com/annonce/..." style="flex:1;min-width:220px"><button id="ownerImportBtn">📥 Importer automatiquement</button></div><p id="ownerImportMsg"></p>';
 const first=section.querySelector('.card'); section.insertBefore(box,first);
 document.getElementById('ownerImportBtn').onclick=async function(){const url=document.getElementById('ownerImportUrl').value.trim(),msg=document.getElementById('ownerImportMsg');if(!url){msg.textContent='Colle le lien de l’annonce.';msg.className='err';return}msg.textContent='Récupération des informations…';msg.className='muted';try{const r=await fetch('/api/import-url',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({url})});const x=await r.json();if(!r.ok)throw Error(x.error||'Import impossible');msg.textContent=x.duplicate?'⚠️ Cette annonce est déjà dans LOGEO.':'✅ Annonce importée dans LOGEO !';msg.className='ok';document.getElementById('ownerImportUrl').value='';if(typeof loadOwner==='function')loadOwner()}catch(e){msg.textContent='❌ '+e.message;msg.className='err'}};
}
function boot(){setTimeout(addOwnerImporter,300)}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',boot);else boot();
})();
