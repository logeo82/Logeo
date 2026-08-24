// Carte LOGEO — affichage à l'échelle de la ville, sans stocker la position de l'étudiant.
let logeoMap, logeoMarkers=[];
function initLogeoMap(){
  if(logeoMap) return logeoMap;
  logeoMap=L.map('map',{scrollWheelZoom:false}).setView([44.0176,1.3541],11);
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',{maxZoom:19,attribution:'&copy; OpenStreetMap'}).addTo(logeoMap);
  return logeoMap;
}
async function geocodeCity(city){
  const key='logeo_geo_'+city.toLowerCase().trim();
  try{const cached=sessionStorage.getItem(key);if(cached)return JSON.parse(cached)}catch(e){}
  const r=await fetch('https://nominatim.openstreetmap.org/search?format=jsonv2&limit=1&countrycodes=fr&q='+encodeURIComponent(city));
  if(!r.ok)throw Error('géocodage indisponible');
  const x=await r.json(); if(!x.length) return null;
  const p={lat:+x[0].lat,lon:+x[0].lon};
  try{sessionStorage.setItem(key,JSON.stringify(p))}catch(e){}
  return p;
}
async function showLogeoMap(listings){
  const map=initLogeoMap();
  logeoMarkers.forEach(m=>m.remove());logeoMarkers=[];
  const groups={};listings.forEach(l=>(groups[l.city]??=[]).push(l));
  const bounds=[];
  for(const [city,rows] of Object.entries(groups)){
    try{
      const p=await geocodeCity(city);if(!p)continue;
      bounds.push([p.lat,p.lon]);
      const best=rows[0];
      const marker=L.marker([p.lat,p.lon]).addTo(map).bindPopup('<b>'+escapeHtml(city)+'</b><br>'+rows.length+' logement(s)<br><span>'+escapeHtml(best.title)+'</span>');
      logeoMarkers.push(marker);
    }catch(e){}
  }
  if(bounds.length)map.fitBounds(bounds,{padding:[25,25],maxZoom:13});
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
function escapeHtml(s){return String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))}
