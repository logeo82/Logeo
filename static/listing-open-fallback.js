// LOGEO: ouverture directe de l'annonce source.
// Stratégie volontairement simple : ne dépend pas de /api/listing/<id>.
(function () {
  function getSourceUrl(card) {
    if (!card) return null;
    const direct = card.getAttribute('data-source-url') || card.dataset.sourceUrl;
    if (direct && /^https?:\/\//i.test(direct)) return direct;
    const link = card.querySelector('a[href]');
    if (link && /^https?:\/\//i.test(link.href)) return link.href;
    return null;
  }

  document.addEventListener('click', function (e) {
    const card = e.target.closest && e.target.closest('[data-listing-id]');
    if (!card || e.target.closest('button,input,select,textarea')) return;

    const url = getSourceUrl(card);
    if (!url) return;

    e.preventDefault();
    e.stopImmediatePropagation();
    window.open(url, '_blank', 'noopener,noreferrer');
  }, true);
})();
