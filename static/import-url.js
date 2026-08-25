(function(){
function addImportBox(){
 if(document.getElementById('logeoImportBox'))return;
 const target=document.querySelector('#studentApp .card')||document.querySelector('main'); if(!target)return;
 const box=document.createElement('div'); box.id='logeoImportBox'; box.className='card'; box.innerHTML='<h2>🔗 Ajouter une annonce</h2><p class="muted">Colle simplement le lien d’une annonce immobilière publique.</p><div style="display:flex;gap:8px;flex-wrap:wrap"><input id="logeoImportUrl" placeholder="https://www.bienici.com/annonce/..." style="flex:1;min-width:220px"><button id="logeoImportBtn">📥 Importer l’annonce</button></div><p id="logeoImportMsg"></p>';
 target.parentNode.insertBefore(box,target);
 document.getElementById('logeoImportBtn').onclick=async function(){const url=document.getElementById('logeoImportUrl').value.trim(),msg=document.getElementById('logeoImportMsg');if(!url){msg.textContent='Colle le lien de l’annonce.';msg.className='err';return}msg.textContent='Récupération de l’annonce…';msg.className='muted';try{const r=await fetch('/api/import-url',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({url})}),x=await r.json();if(!r.ok)throw Error(x.error||'Import impossible');msg.textContent=x.duplicate?'Cette annonce est déjà dans LOGEO.':'Annonce importée avec succès !';msg.className='ok';document.getElementById('logeoImportUrl').value='';if(typeof loadMatches==='function')await loadMatches();}catch(e){msg.textContent=e.message;msg.className='err'}};
}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',addImportBox);else addImportBox();
})();
