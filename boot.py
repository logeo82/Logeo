import os
from pathlib import Path

BASE = Path(__file__).resolve().parent
INDEX = BASE / 'static' / 'index.html'
MARKER = '<!-- LOGEO_OWNER_IMPORT -->'
BLOCK = r'''<!-- LOGEO_OWNER_IMPORT -->
<div class="card" id="ownerImportBox" style="border:2px solid #dbe4ff">
  <h3>🔗 Importer une annonce depuis une URL</h3>
  <p class="muted">Colle le lien public d'une annonce immobilière (Bien'ici, SeLoger, etc.).</p>
  <div class="grid">
    <label>URL de l'annonce<input id="ownerImportUrl" type="url" placeholder="https://www.bienici.com/annonce/..."></label>
    <div style="display:flex;align-items:end"><button type="button" onclick="importOwnerListing()">📥 Importer automatiquement</button></div>
  </div>
  <p id="ownerImportMsg" class="muted"></p>
</div>
<script>
async function importOwnerListing(){
  const input=document.getElementById('ownerImportUrl'), msg=document.getElementById('ownerImportMsg');
  const url=(input.value||'').trim();
  if(!url){msg.textContent='Colle d’abord le lien de l’annonce.';msg.className='err';return;}
  msg.textContent='Récupération de l’annonce…';msg.className='muted';
  try{
    const r=await fetch('/api/import-url',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({url})});
    const x=await r.json();
    if(!r.ok) throw new Error(x.error||'Import impossible');
    msg.textContent=x.duplicate?'Cette annonce est déjà présente dans LOGEO.':'Annonce importée avec succès !';
    msg.className='ok';
    input.value='';
    if(typeof loadOwner==='function') await loadOwner();
  }catch(e){msg.textContent=e.message;msg.className='err';}
}
</script>
'''
text = INDEX.read_text(encoding='utf-8')
if MARKER not in text:
    marker = '<h3>Nouvelle annonce</h3>'
    if marker not in text:
        raise SystemExit('owner form marker not found')
    text = text.replace(marker, BLOCK + marker, 1)
    INDEX.write_text(text, encoding='utf-8')

from app import app
import importer  # registers /api/import-url
from waitress import serve
serve(app, host='0.0.0.0', port=int(os.environ.get('PORT','5000')))
