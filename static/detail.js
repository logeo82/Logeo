/* LOGEO - fiche logement détaillée + carte simulée */
(function(){
  function esc(v){return String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));}

  const SIM={
    'Studio centre-ville':{lat:44.0142,lon:1.3378,quartier:'Villebourbon',distance:'1,4 km'},
    'T1 proche établissements':{lat:44.0268,lon:1.3748,quartier:'Beausoleil',distance:'2,8 km'},
    'Studio rénové':{lat:44.0392,lon:1.3635,quartier:'Fonneuve',distance:'3,8 km'},
    'T2 avec balcon':{lat:43.9948,lon:1.3490,quartier:'Sapiac / Pech Boyer',distance:'4,2 km'}
  };
  const fallback={lat:44.0176,lon:1.3541,quartier:'Montauban',distance:'—'};
  function simFor(l){return SIM[l?.title]||fallback;}

  window.openListingDetail=function(id){
    const l=(window.allMatches||[]).find(x=>Number(x.id)===Number(id));
    if(!l)return;
    let modal=document.getElementById('listingDetailModal');
    if(!modal){
      modal=document.createElement('div');modal.id='listingDetailModal';
      modal.innerHTML='<div class="listing-detail-backdrop" aria-hidden="true"></div><div class="listing-detail-panel" role="dialog" aria-modal="true"><button type="button" class="listing-detail-close" aria-label="Fermer la fiche">×</button><div id="listingDetailContent"></div></div>';
      document.body.appendChild(modal);
      const closeBtn=modal.querySelector('.listing-detail-close');
      const backdrop=modal.querySelector('.listing-detail-backdrop');
      closeBtn.addEventListener('click',function(e){e.preventDefault();e.stopPropagation();window.closeListingDetail();});
      backdrop.addEventListener('click',function(e){e.preventDefault();e.stopPropagation();window.closeListingDetail();});
    }
    const photos=Array.from({length:8},(_,i)=>`<div class="listing-photo ${i===0?'listing-photo-main':''}"><span>📷</span><small>Photo ${i+1}</small></div>`).join('');
    const reasons=(l.reasons||[]).map(r=>`<span class="tag">${esc(r)}</span>`).join('');
    const furnished=l.furnished?'Oui':'Non',s=simFor(l);
    document.getElementById('listingDetailContent').innerHTML=`
      <div class="listing-gallery">${photos}</div>
      <div class="listing-detail-body">
        <div class="listing-detail-score ${l.score>=85?'green':l.score>=70?'orange':''}">${esc(l.score)}% compatible</div>
        <h1>${esc(l.title)}</h1>
        <div class="listing-detail-price">${esc(l.price)} € <span>/ mois</span></div>
        <div class="listing-detail-location">📍 ${esc(l.city)} · localisation approximative</div>
        <div class="listing-detail-stats"><div><b>${esc(l.surface)} m²</b><span>Surface</span></div><div><b>${esc(l.type)}</b><span>Type</span></div><div><b>${furnished}</b><span>Meublé</span></div><div><b>${esc(l.available_date||'NC')}</b><span>Disponible</span></div></div>
        <section><h2>⭐ Pourquoi ce logement vous correspond</h2><div>${reasons||'<span class="tag">Correspondance personnalisée</span>'}</div></section>
        <section><h2>📝 Description</h2><p>${esc(l.description||'Aucune description détaillée pour le moment.')}</p></section>
        <section><h2>📍 Localisation</h2><p><b>${esc(s.quartier)}</b> · ${esc(s.distance)}</p><div id="listingMiniMap" class="listing-mini-map" style="height:240px;border-radius:12px;overflow:hidden;border:1px solid #d6dbe5"></div></section>
        <div class="listing-detail-actions"><button type="button" onclick="fav(${Number(l.id)});closeListingDetail()">${l.favorite?'💔 Retirer des favoris':'❤️ Ajouter aux favoris'}</button><button type="button" class="secondary" onclick="apply(${Number(l.id)});closeListingDetail()">${l.application?'🟠 Candidature envoyée':'📄 Je candidate'}</button></div>
      </div>`;
    modal.classList.add('open');modal.style.display='block';document.body.classList.add('listing-modal-open');

    setTimeout(()=>{
      const el=document.getElementById('listingMiniMap');
      if(!el||typeof L==='undefined')return;
      const map=L.map(el,{scrollWheelZoom:false,dragging:true,zoomControl:true}).setView([s.lat,s.lon],14);
      L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',{maxZoom:19,attribution:'© OpenStreetMap'}).addTo(map);
      L.marker([s.lat,s.lon]).addTo(map).bindPopup(`<b>${esc(s.quartier)}</b><br>${esc(s.distance)} du centre de Montauban`).openPopup();
      setTimeout(()=>map.invalidateSize(),100);
    },0);
  };

  window.closeListingDetail=function(){
    const m=document.getElementById('listingDetailModal');
    if(m){m.classList.remove('open');m.style.display='none';}
    document.body.classList.remove('listing-modal-open');
  };
  document.addEventListener('keydown',e=>{if(e.key==='Escape')window.closeListingDetail();});

  /* Remplace la carte réelle utilisée par index.html par la carte simulée. */
  window.showMap=async function(rows){
    if(typeof initMap==='function')initMap();
    if(!window.logeoMap)return;
    if(Array.isArray(window.logeoMarkers))window.logeoMarkers.forEach(m=>m.remove());
    window.logeoMarkers=[];
    const points=[];
    rows.forEach(l=>{
      const s=simFor(l);points.push([s.lat,s.lon]);
      const marker=L.marker([s.lat,s.lon]).addTo(window.logeoMap).bindPopup(`<b>${esc(l.title)}</b><br>📍 ${esc(s.quartier)}<br>📏 ${esc(s.distance)}<br>💶 ${esc(l.price)} € / mois<br>⭐ ${esc(l.score)}% compatible`);
      window.logeoMarkers.push(marker);
    });
    if(points.length)window.logeoMap.fitBounds(points,{padding:[25,25],maxZoom:14});
    setTimeout(()=>window.logeoMap.invalidateSize(),100);
  };

  let studentMarker=null;
  window.locateStudent=function(){
    if(!navigator.geolocation){alert('La géolocalisation n’est pas disponible.');return;}
    navigator.geolocation.getCurrentPosition(p=>{
      if(typeof initMap==='function')initMap();
      const pos=[p.coords.latitude,p.coords.longitude];
      if(studentMarker)studentMarker.remove();
      studentMarker=L.circleMarker(pos,{radius:9,weight:3,fillOpacity:.85}).addTo(window.logeoMap).bindPopup('📍 Votre position approximative').openPopup();
      window.logeoMap.setView(pos,13);
    },()=>alert('Position non accessible. Vérifiez les autorisations de localisation.'));
  };
})();
