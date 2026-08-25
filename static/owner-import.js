(function(){
function addOwnerImporter(){
 const section=document.getElementById('ownerApp');
 if(!section||document.getElementById('ownerImportBox')) return !!section;
 const box=document.createElement('div'); box.id='ownerImportBox'; box.className='card'; box.style.marginBottom='16px';
 box.innerHTML='<h3>🔗 Importer une annonce depuis une URL</h3><p class="muted">Colle le lien public d’une annonce Bien’ici ou d’un autre site immobilier.</p><div style="display:flex;gap:8px;flex-wrap:wrap"><input id="ownerImportUrl" type="url" placeholder="https://www.bienici.com/annonce/..." style="flex:1;min-width:220px"><button id="ownerImportBtn" type="button">📥 Importer automatiquement</button></div><p id="ownerImportMsg"></p>';
 const first=section.querySelector('.card'); if(first) section.insertBefore(box,first); else section.prepend(box);
 document.getElementById('ownerImportBtn').onclick=async function(){
  const url=document.getElementById('ownerImportUrl').value.trim(), msg=document.getElementById('ownerImportMsg');
  if(!url){msg.textContent='Colle le lien de l’annonce.';msg.className='err';return;}
  msg.textContent='Récupération des informations…';msg.className='muted';
  try{
   const r=await fetch('/api/import-url',{method:'POST',headers:{'Content-Type':'application/json','Accept':'application/json'},body:JSON.stringify({url})});
   const raw=await r.text();
   let x=null;
   try{x=JSON.parse(raw)}catch(_){
     const looksHtml=/^\s*<!doctype|^\s*<html/i.test(raw);
     throw Error(looksHtml?'Le serveur a renvoyé une page HTML au lieu de la réponse LOGEO. Le déploiement Railway n’est probablement pas à jour.':'Réponse serveur invalide (HTTP '+r.status+').');
   }
   if(!r.ok) throw Error(x.error||('Import impossible (HTTP '+r.status+')'));
   msg.textContent=x.duplicate?'⚠️ Cette annonce est déjà dans LOGEO.':'✅ Annonce importée dans LOGEO !';msg.className='ok';
   document.getElementById('ownerImportUrl').value='';if(typeof loadOwner==='function')loadOwner();
  }catch(e){msg.textContent='❌ '+e.message;msg.className='err'}
 };
 return true;
}
function boot(){addOwnerImporter();const obs=new MutationObserver(function(){if(addOwnerImporter())obs.disconnect()});obs.observe(document.body,{childList:true,subtree:true});setTimeout(function(){obs.disconnect();addOwnerImporter()},30000)}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',boot);else boot();
})();
