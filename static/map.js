// Carte LOGEO — simulation des quartiers de Montauban.
const LOGEO_SIMULATION={
  'Studio centre-ville':{quartier:'Villebourbon',distance:'1,4 km',lat:44.0128,lon:1.3378},
  'T1 proche établissements':{quartier:'Beausoleil',distance:'2,8 km',lat:44.0248,lon:1.3725},
  'Studio rénové':{quartier:'Fonneuve',distance:'3,8 km',lat:44.0470,lon:1.3545},
  'T2 avec balcon':{quartier:'Sapiac',distance:'4,2 km',lat:43.9965,lon:1.3505}
};
let logeoMap,logeoMarkers=[];
function initLogeoMap(){
  if(logeoMap)return logeoMap;
  logeoMap=L.map('map',{scrollWheelZoom:false}).setView([44.0176,1.3541],12);
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',{maxZoom:19,attribution:'&copy; OpenStreetMap'}).addTo(logeoMap);
  return logeoMap;
}
function escapeHtml(s){return String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))}
function simulationFor(l){return LOGEO_SIMULATION[l.title]||null}
function showLogeoMap(listings){
  const map=initLogeoMap();
  logeoMarkers.forEach(m=>m.remove());logeoMarkers=[];
  const bounds=[];
  listings.forEach(l=>{
    const s=simulationFor(l);
    if(!s)return;
    const marker=L.marker([s.lat,s.lon]).addTo(map);
    marker.bindPopup('<b>'+escapeHtml(l.title)+'</b><br>📍 Quartier : <b>'+escapeHtml(s.quartier)+'</b><br>📏 Distance : '+escapeHtml(s.distance)+'<br>💶 '+escapeHtml(l.price)+' € / mois<br>⭐ '+escapeHtml(l.score)+'% compatible');
    logeoMarkers.push(marker);bounds.push([s.lat,s.lon]);
  });
  if(bounds.length)map.fitBounds(bounds,{padding:[30,30],maxZoom:13});
  setTimeout(()=>map.invalidateSize(),100);
}
function locateStudent(){
  if(!navigator.geolocation){alert('La géolocalisation n’est pas disponible sur cet appareil.');return}
  navigator.geolocation.getCurrentPosition(pos=>{
    const map=initLogeoMap(),p=[pos.coords.latitude,pos.coords.longitude];
    L.circleMarker(p,{radius:8}).addTo(map).bindPopup('Votre position (non enregistrée par LOGEO)').openPopup();
    map.setView(p,13);
  },()=>alert('Position non accessible. Vérifiez l’autorisation de localisation du navigateur.'));
}
// L'ancien index possède encore ses fonctions de carte inline : on les remplace après son chargement.
setTimeout(()=>{
  if(typeof initMap==='function')window.initMap=initLogeoMap;
  if(typeof showMap==='function')window.showMap=showLogeoMap;
  if(typeof locateStudent==='function')window.locateStudent=locateStudent;
},0);
