// Carte LOGEO — simulation des quartiers de Montauban + normalisation des tracés Valhalla.
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
function escapeHtml(s){return String(s??'').replace(/[&<>\"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','\"':'&quot;',"'":'&#39;'}[c]))}
function simulationFor(l,index){
  if(LOGEO_SIMULATION[l?.title])return LOGEO_SIMULATION[l.title];
  const fallback=[
    {quartier:'Villebourbon',distance:'1,4 km',lat:44.0128,lon:1.3378},
    {quartier:'Beausoleil',distance:'2,8 km',lat:44.0248,lon:1.3725},
    {quartier:'Fonneuve',distance:'3,8 km',lat:44.0470,lon:1.3545},
    {quartier:'Sapiac',distance:'4,2 km',lat:43.9965,lon:1.3505}
  ];
  return fallback[index%fallback.length];
}
function showLogeoMap(listings){
  const map=initLogeoMap();
  logeoMarkers.forEach(m=>m.remove());logeoMarkers=[];
  const bounds=[];
  listings.forEach((l,i)=>{
    const s=simulationFor(l,i);
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
    if(window.logeoStudentMarker)window.logeoStudentMarker.remove();
    window.logeoStudentMarker=L.circleMarker(p,{radius:9,weight:3,fillOpacity:.85}).addTo(map).bindPopup('📍 Votre position approximative').openPopup();
    map.setView(p,13);
  },()=>alert('Position non accessible. Vérifiez l’autorisation de localisation du navigateur.'));
}

// Valhalla renvoie normalement la géométrie d'une étape sous forme de polyline6.
// On la normalise ici en GeoJSON afin que Leaflet puisse toujours dessiner le tracé,
// même lorsque l'instance publique ignore shape_format=geojson.
function decodePolyline6(encoded){
  let index=0,lat=0,lon=0,coords=[];
  while(index<encoded.length){
    let result=0,shift=0,b;
    do{b=encoded.charCodeAt(index++)-63;result|=(b&31)<<shift;shift+=5}while(b>=32);
    const dlat=result&1?~(result>>1):(result>>1);lat+=dlat;
    result=0;shift=0;
    do{b=encoded.charCodeAt(index++)-63;result|=(b&31)<<shift;shift+=5}while(b>=32);
    const dlon=result&1?~(result>>1):(result>>1);lon+=dlon;
    coords.push([lon/1e6,lat/1e6]);
  }
  return coords;
}
function routeShapeToGeoJSON(shape){
  if(!shape)return null;
  if(typeof shape==='object'){
    if(shape.type==='Feature'||shape.type==='FeatureCollection'||shape.type==='LineString')return shape;
    if(Array.isArray(shape.coordinates))return {type:'Feature',properties:{},geometry:shape};
  }
  if(typeof shape==='string')return {type:'Feature',properties:{},geometry:{type:'LineString',coordinates:decodePolyline6(shape)}};
  return null;
}
(function installValhallaShapeFix(){
  const originalFetch=window.fetch.bind(window);
  window.fetch=async function(input,init){
    const response=await originalFetch(input,init);
    let url='';
    try{url=typeof input==='string'?input:(input&&input.url)||''}catch(e){}
    if(!url.includes('valhalla1.openstreetmap.de/route')||!response.ok)return response;
    try{
      const data=await response.clone().json();
      const trip=data.trip;
      const raw=trip&&(trip.shape||(trip.legs&&trip.legs[0]&&trip.legs[0].shape));
      const normalized=routeShapeToGeoJSON(raw);
      if(!normalized)return response;
      data.trip.shape=normalized;
      return new Response(JSON.stringify(data),{status:response.status,statusText:response.statusText,headers:{'Content-Type':'application/json'}});
    }catch(e){return response}
  };
})();

setTimeout(()=>{
  try{
    initMap=initLogeoMap;
    showMap=showLogeoMap;
    window.initMap=initLogeoMap;
    window.showMap=showLogeoMap;
    window.locateStudent=locateStudent;
  }catch(e){console.error('LOGEO map override',e)}
},0);
