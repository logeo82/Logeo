/* LOGEO - fiche logement détaillée, ajout isolé */
(function(){
  function esc(v){return String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));}
  window.openListingDetail=function(id){
    const l=(window.allMatches||[]).find(x=>Number(x.id)===Number(id));
    if(!l)return;
    let modal=document.getElementById('listingDetailModal');
    if(!modal){
      modal=document.createElement('div');modal.id='listingDetailModal';
      modal.innerHTML='<div class="listing-detail-backdrop" onclick="closeListingDetail(event)"></div><div class="listing-detail-panel" role="dialog" aria-modal="true"><button class="listing-detail-close" onclick="closeListingDetail()">×</button><div id="listingDetailContent"></div></div>';
      document.body.appendChild(modal);
    }
    const photos=Array.from({length:8},(_,i)=>`<div class="listing-photo ${i===0?'listing-photo-main':''}"><span>📷</span><small>Photo ${i+1}</small></div>`).join('');
    const reasons=(l.reasons||[]).map(r=>`<span class="tag">${esc(r)}</span>`).join('');
    const furnished=l.furnished?'Oui':'Non';
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
        <section><h2>📍 Localisation</h2><div class="listing-mini-map">Localisation approximative à l'échelle de ${esc(l.city)}</div></section>
        <div class="listing-detail-actions"><button onclick="fav(${Number(l.id)});closeListingDetail()">${l.favorite?'💔 Retirer des favoris':'❤️ Ajouter aux favoris'}</button><button class="secondary" onclick="apply(${Number(l.id)});closeListingDetail()">${l.application?'🟠 Candidature envoyée':'📄 Je candidate'}</button></div>
      </div>`;
    modal.classList.add('open');document.body.classList.add('listing-modal-open');
  };
  window.closeListingDetail=function(e){if(e&&e.target&&e.target.classList.contains('listing-detail-panel'))return;const m=document.getElementById('listingDetailModal');if(m)m.classList.remove('open');document.body.classList.remove('listing-modal-open');};
  document.addEventListener('keydown',e=>{if(e.key==='Escape')closeListingDetail();});
})();
