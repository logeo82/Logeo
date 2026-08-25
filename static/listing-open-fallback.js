// LOGEO: fallback d'ouverture des annonces importées.
// Ne remplace pas detail.js et ne modifie pas le backend.
(function () {
  async function fetchListing(id) {
    const r = await fetch('/api/listing/' + encodeURIComponent(id), {
      headers: { 'Accept': 'application/json' },
      credentials: 'same-origin'
    });
    if (!r.ok) throw new Error('Impossible de récupérer cette annonce');
    const data = await r.json();
    return data.listing;
  }

  function originalUrl(listing) {
    return listing && listing.source_url && /^https?:\/\//i.test(listing.source_url)
      ? listing.source_url : null;
  }

  async function openImportedListingFallback(id) {
    try {
      let listing = (window.allMatches || []).find(x => Number(x.id) === Number(id));
      if (!listing) listing = await fetchListing(id);

      // Si la fiche native existe et accepte l'objet directement, on la réutilise.
      if (typeof window.renderListingDetail === 'function') {
        window.renderListingDetail(listing);
        return;
      }
      if (typeof window.openListingDetail === 'function') {
        try { window.openListingDetail(id); return; } catch (_) {}
      }

      // Fallback autonome : affiche les informations essentielles sans modifier l'UI existante.
      const old = document.getElementById('logeoImportedDetailFallback');
      if (old) old.remove();
      const wrap = document.createElement('div');
      wrap.id = 'logeoImportedDetailFallback';
      wrap.style.cssText = 'position:fixed;inset:0;background:#0008;z-index:10000;padding:4vh 4vw;overflow:auto';
      const card = document.createElement('div');
      card.style.cssText = 'background:#fff;max-width:850px;margin:auto;border-radius:18px;padding:24px;position:relative';
      const photos = Array.isArray(listing.photos) ? listing.photos : [];
      const gallery = photos.map(u => '<img src="' + String(u).replace(/"/g,'&quot;') + '" style="width:100%;max-height:260px;object-fit:cover;border-radius:10px">').join('');
      card.innerHTML = '<button id="logeoCloseDetail" style="float:right">✕</button>' +
        (gallery ? '<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:8px;margin-bottom:18px">'+gallery+'</div>' : '') +
        '<h1>'+escapeHtml(listing.title || 'Annonce')+'</h1>' +
        '<h2>'+escapeHtml(String(listing.price ?? ''))+' €</h2>' +
        '<p>'+escapeHtml(listing.city || '')+' · '+escapeHtml(String(listing.surface ?? ''))+' m² · '+escapeHtml(listing.type || '')+'</p>' +
        '<p>'+escapeHtml(listing.description || '')+'</p>' +
        (originalUrl(listing) ? '<p><a href="'+escapeHtml(originalUrl(listing))+'" target="_blank" rel="noopener">Voir l’annonce originale</a></p>' : '');
      wrap.appendChild(card); document.body.appendChild(wrap);
      document.getElementById('logeoCloseDetail').onclick = () => wrap.remove();
      wrap.onclick = e => { if (e.target === wrap) wrap.remove(); };
    } catch (e) {
      alert(e.message || 'Impossible d’ouvrir cette annonce.');
    }
  }

  function escapeHtml(v) {
    return String(v).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  }

  window.openImportedListingFallback = openImportedListingFallback;

  // Permet aux cartes existantes d'utiliser le fallback sans modifier leur HTML.
  document.addEventListener('click', function (e) {
    const card = e.target.closest && e.target.closest('[data-listing-id]');
    if (!card || e.target.closest('button,a,input,select,textarea')) return;
    const id = card.getAttribute('data-listing-id');
    if (id) {
      e.preventDefault();
      openImportedListingFallback(id);
    }
  }, true);
})();
