/* LOGEO - route renderer, preserves destination search */
(function(){
const previous=window.openListingDetail;
function decodeShape(s){if(!s)return null;if(typeof s==='object')return s;try{return JSON.parse(s)}catch(e){return null}}
function drawStreetRoute(route, start, end, label){const el=document.getElementById('routeMap');if(!el||typeof L==='undefined'||!route)return;window.__logeoRouteMap&&window.__logeoRouteMap.remove();const map=L.map(el,{scrollWheelZoom:false,zoomControl:true});window.__logeoRouteMap=map;L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',{maxZoom:19,attribution:'© OpenStreetMap contributors'}).addTo(map);const geo=decodeShape(route.shape);if(geo){const line=L.geoJSON(geo,{style:{weight:6,opacity:.9}}).addTo(map);map.fitBounds(line.getBounds(),{padding:[30,30],maxZoom:16})}else map.fitBounds([[start.lat,start.lon],[end.lat,end.lon]],{padding:[30,30]});L.marker([start.lat,start.lon]).addTo(map).bindPopup('🏠 Appartement');L.marker([end.lat,end.lon]).addTo(map).bindPopup(label||'🎯 Destination');setTimeout(()=>map.invalidateSize(),300);setTimeout(()=>map.invalidateSize(),1000)}
window.logeoDrawStreetRoute=drawStreetRoute;
if(typeof previous==='function')window.openListingDetail=function(id){previous(id);setTimeout(()=>{const el=document.getElementById('routeMap');if(el)el.dataset.streetRoute='ready'},800)};
})();