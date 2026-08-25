(function(){
function addImportBox(){
 if(document.getElementById('logeoImportBox'))return;
 const owner=document.getElementById('ownerApp');
 const target=owner||document.querySelector('main'); if(!target)return;
 const box=document.createElement('div'); box.id='logeoImportBox'; box.className='card'; box.innerHTML='<h3>🔗 Importer une annonce depuis un site immobilier</h3><p class="muted">Colle le lien public d’une annonce Bien’ici, SeLoger, etc.</p><div style="display:flex;gap:8px;flex-wrap:wrap"><input id="logeoImportUrl" type="url" placeholder="https://www.bienici.com/annonce/..." style="flex:1;min-width:220px"><button id="logeoImportBtn">📥 Importer l’annonce</button></div><p id="logeoImportMsg"></p>';
 const form=owner.querySelector('.card'); if(form) owner.insertBefore(box,form); else target.insertBefore(box,target.firstChild);
 document.getElementById('logeoImportBtn').onclick=async function(){const url=document.getElementById('logeoImportUrl').value.trim(),msg=document.getElementById('logeoImportMsg');if(!url){msg.textContent='Colle le lien de l’annonce.';msg.className='err';return}msg.textContent='Récupération des informations…';msg.className='muted';try{const r=await fetch('/api/import-url',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({url})}),x=await r.json();if(!r.ok)throw Error(x.error||'Import impossible');msg.textContent=x.duplicate?'Cette annonce est déjà dans LOGEO.':'✅ Annonce importée dans tes annonces !';msg.className='ok';document.getElementById('logeoImportUrl').value='';if(typeof loadOwner==='function')loadOwner()}catch(e){msg.textContent='❌ '+e.message;msg.className='err'}};
}
function wait(){if(document.getElementById('ownerApp'))addImportBox();else setTimeout(wait,100)}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',wait);else wait();
})();
