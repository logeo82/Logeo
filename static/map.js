// Carte LOGEO — logements sur la carte
const LOGEO_SIMULATION={
  'Studio centre-ville':{quartier:'Villebourbon',distance:'1,4 km',lat:44.0128,lon:1.3378},
  'T1 proche établissements':{quartier:'Beausoleil',distance:'2,8 km',lat:44.0248,lon:1.3725},
  'Studio rénové':{quartier:'Fonneuve',distance:'3,8 km',lat:44.0470,lon:1.3545},
  'T2 avec balcon':{quartier:'Sapiac',distance:'4,2 km',lat:43.9965,lon:1.3505}
};
let logeoMapOverride,logeoMarkersOverride=[];
function initLogeoMapOverride(){
  if(logeoMapOverride)return logeoMapOverride;
  logeoMapOverride=L.map('map',{scrollWheelZoom:false}).setView([44.0176,1.3541],12);
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',{maxZoom:19,attribution:'© OpenStreetMap contributors'}).addTo(logeoMapOverride);
  return logeoMapOverride;
}
function escMap(s){return String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))}
function simMap(l,i){return LOGEO_SIMULATION[l?.title]||[
 {quartier:'Villebourbon',distance:'1,4 km',lat:44.0128,lon:1.3378},
 {quartier:'Beausoleil',distance:'2,8 km',lat:44.0248,lon:1.3725},
 {quartier:'Fonneuve',distance:'3,8 km',lat:44.0470,lon:1.3545},
 {quartier:'Sapiac',distance:'4,2 km',lat:43.9965,lon:1.3505}
][i%4]}
function showMapOverride(listings){
  const map=initLogeoMapOverride();
  logeoMarkersOverride.forEach(m=>m.remove());logeoMarkersOverride=[];
  const bounds=[];
  (listings||[]).forEach((l,i)=>{
    const s=simMap(l,i),m=L.marker([s.lat,s.lon]).addTo(map);
    m.bindPopup('<b>'+escMap(l.title)+'</b><br>📍 '+escMap(s.quartier)+'<br>📏 '+escMap(s.distance)+'<br>💶 '+escMap(l.price)+' € / mois');
    m.on('click',()=>{if(typeof window.openListingDetail==='function')window.openListingDetail(l.id)});
    logeoMarkersOverride.push(m);bounds.push([s.lat,s.lon]);
  });
  if(bounds.length)map.fitBounds(bounds,{padding:[30,30],maxZoom:14});
  setTimeout(()=>map.invalidateSize(),100);
}
function locateStudentOverride(){
 if(!navigator.geolocation)return alert('La géolocalisation n’est pas disponible.');
 navigator.geolocation.getCurrentPosition(p=>{const map=initLogeoMapOverride(),pos=[p.coords.latitude,p.coords.longitude];if(window.logeoStudentMarker)window.logeoStudentMarker.remove();window.logeoStudentMarker=L.circleMarker(pos,{radius:9,weight:3,fillOpacity:.85}).addTo(map).bindPopup('📍 Votre position approximative').openPopup();map.setView(pos,13)},()=>alert('Position non accessible. Vérifiez l’autorisation de localisation.'));
}
function injectOwnerImporter(){
  const section=document.getElementById('ownerApp');
  if(!section || document.getElementById('ownerImportBox')) return;
  const box=document.createElement('div');
  box.id='ownerImportBox'; box.className='card';
  box.style.cssText='margin:0 0 16px;border:2px solid #dbe4ff;background:#f8faff';
  box.innerHTML='<h3>🔗 Importer une annonce depuis une URL</h3><p class="muted">Colle le lien public d’une annonce Bien’ici, SeLoger ou d’un autre site immobilier.</p><div style="display:flex;gap:8px;flex-wrap:wrap"><input id="ownerImportUrl" type="url" placeholder="https://www.bienici.com/annonce/..." style="flex:1;min-width:220px"><button id="ownerImportBtn" type="button">📥 Importer automatiquement</button></div><p id="ownerImportMsg"></p>';
  const first=section.querySelector('.card');
  if(first) section.insertBefore(box,first); else section.prepend(box);
  const btn=document.getElementById('ownerImportBtn');
  btn.onclick=async function(){
    const input=document.getElementById('ownerImportUrl'),msg=document.getElementById('ownerImportMsg'),url=input.value.trim();
    if(!url){msg.textContent='Colle le lien de l’annonce.';msg.className='err';return;}
    msg.textContent='Récupération de l’annonce…';msg.className='muted';btn.disabled=true;
    try{
      const r=await fetch('/api/import-url',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({url})});
      const x=await r.json();
      if(!r.ok)throw Error(x.error||'Import impossible');
      msg.textContent=x.duplicate?'⚠️ Cette annonce est déjà dans LOGEO.':'✅ Annonce importée dans Mes annonces !';msg.className='ok';input.value='';
      if(typeof loadOwner==='function')await loadOwner();
    }catch(e){msg.textContent='❌ '+e.message;msg.className='err';}
    finally{btn.disabled=false;}
  };
}
function startOwnerImporter(){
  injectOwnerImporter();
  const obs=new MutationObserver(()=>{if(document.getElementById('ownerApp'))injectOwnerImporter();});
  obs.observe(document.body,{childList:true,subtree:true});
  setTimeout(()=>obs.disconnect(),30000);
}
window.initMap=initLogeoMapOverride;
window.showMap=showMapOverride;
window.locateStudent=locateStudentOverride;
setTimeout(()=>{if(window.allMatches?.length)showMapOverride(window.allMatches);startOwnerImporter()},100);
