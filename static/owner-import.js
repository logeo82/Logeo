(function(){
function addOwnerImporter(){
 const section=document.getElementById('ownerApp');
 if(!section)return false;
 let box=document.getElementById('ownerImportBox');
 if(!box){
  box=document.createElement('div'); box.id='ownerImportBox'; box.className='card'; box.style.marginBottom='16px';
  box.innerHTML='<h3>🔗 Importer une annonce dans LOGEO</h3><p class="muted">Colle le lien public d’une annonce immobilière. LOGEO analyse les informations et les photos avant de créer une vraie annonce dans sa base.</p><div style="display:flex;gap:8px;flex-wrap:wrap"><input id="ownerImportUrl" type="url" placeholder="https://www.seloger.com/annonces/..." style="flex:1;min-width:220px"><button id="ownerImportBtn" type="button">🔎 Analyser l’annonce</button></div><div id="ownerImportPreview" style="margin-top:14px"></div><p id="ownerImportMsg" style="margin-bottom:0"></p>';
  const first=section.querySelector('.card'); if(first) section.insertBefore(box,first); else section.prepend(box);
 }
 const b=document.getElementById('ownerImportBtn'); if(!b||b.dataset.ready)return true; b.dataset.ready='1';
 b.onclick=async function(){
  const input=document.getElementById('ownerImportUrl'),msg=document.getElementById('ownerImportMsg'),preview=document.getElementById('ownerImportPreview'),url=input.value.trim();
  if(!url){msg.textContent='❌ Colle d’abord le lien de l’annonce.';msg.className='err';return;}
  b.disabled=true;b.textContent='⏳ Analyse…';msg.textContent='Lecture des informations publiques et des photos…';msg.className='muted';preview.innerHTML='';
  try{
   const r=await fetch('/api/import-preview',{method:'POST',headers:{'Content-Type':'application/json','Accept':'application/json'},body:JSON.stringify({url})});
   const raw=await r.text();let x;try{x=JSON.parse(raw)}catch(e){throw Error('Réponse serveur invalide (HTTP '+r.status+').')}
   if(!r.ok)throw Error(x.error||'Analyse impossible');
   const d=x.preview||{},photos=(()=>{try{return Array.isArray(d.photos)?d.photos:JSON.parse(d.photos||'[]')}catch(e){return []}})();
   const esc=v=>String(v==null?'':v).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
   preview.innerHTML='<div class="card" style="border:1px solid #d6dbe5;margin:0"><h3>👀 Aperçu avant importation</h3><div style="display:grid;grid-template-columns:1fr 1fr;gap:8px"><div><b>Titre</b><br>'+esc(d.title)+'</div><div><b>Prix</b><br>'+esc(d.price)+' € / mois</div><div><b>Ville</b><br>'+esc(d.city)+'</div><div><b>Surface</b><br>'+esc(d.surface)+' m²</div><div><b>Type</b><br>'+esc(d.type)+'</div><div><b>Meublé</b><br>'+(d.furnished?'Oui':'Non')+'</div></div><div style="margin-top:10px"><b>Description</b><p style="white-space:pre-wrap">'+esc(d.description||'Non disponible')+'</p></div><div><b>Photos récupérées : '+photos.length+'</b><div style="display:flex;gap:8px;overflow:auto;margin-top:8px">'+(photos.length?photos.slice(0,12).map(u=>'<img src="'+esc(u)+'" loading="lazy" style="width:110px;height:85px;object-fit:cover;border-radius:8px;border:1px solid #d6dbe5">').join(''):'<span class="muted">Aucune photo publique récupérée.</span>')+'</div></div><button id="confirmOwnerImport" type="button" style="margin-top:14px">✅ Créer cette annonce dans LOGEO</button></div>';
   msg.textContent='Analyse terminée. Vérifie l’aperçu puis confirme.';msg.className='ok';
   document.getElementById('confirmOwnerImport').onclick=async function(){
    const c=this;c.disabled=true;c.textContent='⏳ Création…';msg.textContent='Création de l’annonce LOGEO…';msg.className='muted';
    try{
     const ir=await fetch('/api/import-url',{method:'POST',headers:{'Content-Type':'application/json','Accept':'application/json'},body:JSON.stringify({url})});
     const iraw=await ir.text();let ix;try{ix=JSON.parse(iraw)}catch(e){throw Error('Le serveur LOGEO n’a pas renvoyé une réponse valide (HTTP '+ir.status+').')}
     if(!ir.ok)throw Error(ix.error||'Import impossible');
     msg.textContent=ix.duplicate?'⚠️ Cette annonce est déjà dans LOGEO.':'✅ Annonce créée dans LOGEO avec ses informations disponibles.';msg.className='ok';preview.innerHTML='';input.value='';if(typeof loadOwner==='function')loadOwner();
    }catch(e){msg.textContent='❌ '+e.message;msg.className='err';c.disabled=false;c.textContent='✅ Créer cette annonce dans LOGEO'}
   };
  }catch(e){msg.textContent='❌ '+e.message;msg.className='err'}finally{b.disabled=false;b.textContent='🔎 Analyser l’annonce'}
 };
 return true;
}
function loadOwnerDetailScript(){
 if(window.openListingDetail)return Promise.resolve();
 return new Promise(function(resolve,reject){const s=document.createElement('script');s.src='/static/detail.js?v=owner-detail-1';s.onload=resolve;s.onerror=reject;document.head.appendChild(s)});
}
async function wireOwnerListings(){
 const box=document.getElementById('myListings');if(!box||box.dataset.detailWired==='1')return;
 try{const x=await fetch('/api/owner/listings',{credentials:'same-origin',headers:{Accept:'application/json'}}).then(r=>r.json());const listings=Array.isArray(x.listings)?x.listings:[];if(!listings.length){box.dataset.detailWired='1';return}await loadOwnerDetailScript();window.allMatches=listings.map(function(l){return Object.assign({score:100,reasons:[],photos:[]},l)});box.innerHTML='<div class="card"><h2>📢 Mes annonces</h2>'+listings.map(function(l){return '<button type="button" class="secondary logeo-owner-listing" data-owner-listing="'+String(l.id).replace(/"/g,'&quot;')+'" style="display:block;width:100%;text-align:left;margin:10px 0;padding:15px">🏠 <b>'+escapeHtml(l.title||'Annonce')+'</b><br><span class="muted">'+escapeHtml(l.price||'')+' € — '+escapeHtml(l.city||'')+'</span><br><small>👉 Ouvrir la fiche LOGEO</small></button>'}).join('')+'</div>';box.querySelectorAll('[data-owner-listing]').forEach(function(b){b.onclick=function(){window.allMatches=listings.map(function(l){return Object.assign({score:100,reasons:[],photos:[]},l)});window.openListingDetail(Number(b.dataset.ownerListing))}});box.dataset.detailWired='1'}catch(e){}
}
function escapeHtml(v){return String(v==null?'':v).replace(/[&<>"']/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]})}
function boot(){addOwnerImporter();const obs=new MutationObserver(function(){if(addOwnerImporter()){const box=document.getElementById('myListings');if(box&&box.innerHTML.trim()&&box.dataset.detailWired!=='1')wireOwnerListings()}});obs.observe(document.body,{childList:true,subtree:true});setTimeout(function(){obs.disconnect();addOwnerImporter();wireOwnerListings()},30000)}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',boot);else boot();
})();
