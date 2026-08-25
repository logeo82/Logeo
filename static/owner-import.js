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

// Pont propriétaire -> même fiche détaillée que côté étudiant.
// On ne modifie pas l'importateur ni son API : on remplace seulement le rendu
// des « Mes annonces » par des cartes cliquables utilisant openListingDetail().
function loadOwnerDetailScript(){
 if(window.openListingDetail) return Promise.resolve();
 return new Promise(function(resolve,reject){
  const s=document.createElement('script'); s.src='/static/detail.js?v=owner-detail-1';
  s.onload=resolve; s.onerror=reject; document.head.appendChild(s);
 });
}
async function wireOwnerListings(){
 const box=document.getElementById('myListings');
 if(!box || box.dataset.detailWired==='1') return;
 try{
  const x=await fetch('/api/owner/listings',{credentials:'same-origin',headers:{Accept:'application/json'}}).then(r=>r.json());
  const listings=Array.isArray(x.listings)?x.listings:[];
  if(!listings.length){box.dataset.detailWired='1';return;}
  await loadOwnerDetailScript();
  window.allMatches=listings.map(function(l){return Object.assign({score:100,reasons:[],photos:[]},l);});
  box.innerHTML='<div class="card"><h2>📢 Mes annonces</h2>'+listings.map(function(l){
   return '<button type="button" class="secondary logeo-owner-listing" data-owner-listing="'+String(l.id).replace(/"/g,'&quot;')+'" style="display:block;width:100%;text-align:left;margin:10px 0;padding:15px">🏠 <b>'+escapeHtml(l.title||'Annonce')+'</b><br><span class="muted">'+escapeHtml(l.price||'')+' € — '+escapeHtml(l.city||'')+'</span><br><small>👉 Ouvrir la fiche LOGEO</small></button>';
  }).join('')+'</div>';
  box.querySelectorAll('[data-owner-listing]').forEach(function(b){b.onclick=function(){window.allMatches=listings.map(function(l){return Object.assign({score:100,reasons:[],photos:[]},l);});window.openListingDetail(Number(b.dataset.ownerListing));};});
  box.dataset.detailWired='1';
 }catch(e){/* on laisse l'affichage propriétaire normal si le pont échoue */}
}
function escapeHtml(v){return String(v==null?'':v).replace(/[&<>"']/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]})}
function boot(){
 addOwnerImporter();
 const obs=new MutationObserver(function(){
  if(addOwnerImporter()){
   const box=document.getElementById('myListings');
   if(box && box.innerHTML.trim() && box.dataset.detailWired!=='1') wireOwnerListings();
  }
 });
 obs.observe(document.body,{childList:true,subtree:true});
 setTimeout(function(){obs.disconnect();addOwnerImporter();wireOwnerListings()},30000);
}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',boot);else boot();
})();
