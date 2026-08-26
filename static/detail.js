/* LOGEO - fiches annonces avec vraies photos */
(function(){
const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const photosOf=l=>{let p=l?.photos;if(typeof p==='string'){try{p=JSON.parse(p)}catch(e){p=[]}}return Array.isArray(p)?p.filter(x=>typeof x==='string'&&x.trim()).slice(0,30):[]};
window.openListingDetail=async function(id){
 let l=(window.allMatches||[]).find(x=>Number(x.id)===Number(id));
 try{const r=await fetch('/api/listing/'+encodeURIComponent(id),{credentials:'same-origin',headers:{Accept:'application/json'}});if(r.ok){const x=await r.json();if(x.listing)l={...(l||{}),...x.listing}}}catch(e){}
 if(!l)return;
 let m=document.getElementById('listingDetailModal');
 if(!m){m=document.createElement('div');m.id='listingDetailModal';m.innerHTML='<div class="listing-detail-backdrop"></div><div class="listing-detail-panel"><button type="button" class="listing-detail-close">×</button><div id="listingDetailContent"></div></div>';document.body.appendChild(m);m.querySelector('.listing-detail-close').onclick=window.closeListingDetail;m.querySelector('.listing-detail-backdrop').onclick=window.closeListingDetail}
 const p=photosOf(l),gallery=p.length?p.map((u,i)=>'<img class="listing-photo '+(i===0?'listing-photo-main':'')+'" src="'+esc(u)+'" loading="lazy" alt="Photo '+(i+1)+'" onerror="this.style.display=\'none\'">').join(''):'<div class="listing-no-photo listing-photo-main"><span>📷</span><b>Photos indisponibles</b><small>La source n’a pas fourni de photo exploitable.</small></div>';
 const source=l.source_url||l.external_url||'';
 const facts=[['Surface',l.surface?l.surface+' m²':'—'],['Pièces',l.rooms||'—'],['Chambres',l.bedrooms||'—'],['DPE',l.dpe_class||'—'],['Étage',l.floor||'—'],['Parking',l.parking?'Oui':'—'],['Balcon',l.balcony?'Oui':'—'],['Terrasse',l.terrace?'Oui':'—']];
 const desc=l.description||'Aucune description détaillée disponible.';
 document.getElementById('listingDetailContent').innerHTML='<div class="listing-gallery">'+gallery+'</div><div class="listing-detail-body"><div class="listing-detail-score">'+esc(l.score||'')+'% compatible</div><h1>'+esc(l.title)+'</h1><div class="listing-detail-price">'+esc(l.price)+' €</div><div class="listing-detail-location">📍 '+esc(l.address||l.city||'')+'</div><div class="listing-detail-stats">'+facts.map(x=>'<div><b>'+esc(x[1])+'</b><span>'+esc(x[0])+'</span></div>').join('')+'</div><section><h2>📝 Description</h2><p>'+esc(desc).replace(/\n/g,'<br>')+'</p></section><section><h2>🏠 Équipements</h2><p>'+([l.furnished?'Meublé':'',l.garage?'Garage':'',l.cellar?'Cave':'',l.elevator?'Ascenseur':'',l.double_glazing?'Double vitrage':'',l.internet_fiber?'Fibre':''].filter(Boolean).map(esc).join(' · ')||'Informations non renseignées')+'</p></section><div class="listing-detail-actions">'+(source?'<button type="button" class="primary" id="openOriginal">🔗 Ouvrir l’annonce originale</button>':'<span class="muted">Lien source non disponible</span>')+'</div></div>';
 if(source)document.getElementById('openOriginal').onclick=()=>window.open(source,'_blank','noopener,noreferrer');
 m.style.display='block';document.body.classList.add('listing-modal-open');
};
window.closeListingDetail=function(){const m=document.getElementById('listingDetailModal');if(m)m.style.display='none';document.body.classList.remove('listing-modal-open')};
})();
