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
window.initMap=initLogeoMapOverride;
window.showMap=showMapOverride;
window.locateStudent=locateStudentOverride;
setTimeout(()=>{if(window.allMatches?.length)showMapOverride(window.allMatches)},300);
