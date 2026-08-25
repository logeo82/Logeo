/* LOGEO - fiche logement détaillée, ajout isolé */
(function(){
  function esc(v){return String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));}
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
        <div class="listing-detail-actions"><button type="button" onclick="fav(${Number(l.id)});closeListingDetail()">${l.favorite?'💔 Retirer des favoris':'❤️ Ajouter aux favoris'}</button><button type="button" class="secondary" onclick="apply(${Number(l.id)});closeListingDetail()">${l.application?'🟠 Candidature envoyée':'📄 Je candidate'}</button></div>
      </div>`;
    modal.classList.add('open');modal.style.display='block';document.body.classList.add('listing-modal-open');
  };
  window.closeListingDetail=function(){
    const m=document.getElementById('listingDetailModal');
    if(m){m.classList.remove('open');m.style.display='none';}
    document.body.classList.remove('listing-modal-open');
  };
  document.addEventListener('keydown',e=>{if(e.key==='Escape')window.closeListingDetail();});
})();
