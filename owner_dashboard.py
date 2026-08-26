import app as logeo

@logeo.app.after_request
def owner_dashboard_ui(response):
    try:
        if not (response.content_type or '').startswith('text/html'):
            return response
        page = response.get_data(as_text=True)
        if 'id="ownerApp"' not in page or 'ownerDashboardUi' in page:
            return response
        script = r'''<script id="ownerDashboardUi">(function(){
function esc(v){return String(v==null?'':v).replace(/[&<>\"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','\"':'&quot;',"'":'&#39;'}[c]))}
function css(){if(document.getElementById('odStyles'))return;const s=document.createElement('style');s.id='odStyles';s.textContent=`#ownerDashboard{margin-bottom:14px}.od-head{display:flex;justify-content:space-between;align-items:center;gap:10px;flex-wrap:wrap}.od-nav{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-top:14px}.od-nav button{width:100%;min-height:76px;margin:0}.od-profile{background:#f8fafc;border:1px solid #e4e7ec}.od-ct{background:#111827;color:#fff}.od-hide{display:none!important}@media(max-width:650px){.od-nav{grid-template-columns:1fr 1fr}}`;document.head.appendChild(s)}
async function build(){const owner=document.getElementById('ownerApp');if(!owner)return false;if(document.getElementById('ownerDashboard'))return true;let x=null;try{const r=await fetch('/api/me',{headers:{'Accept':'application/json'},cache:'no-store'});if(!r.ok)return true;x=await r.json()}catch(e){return true}if(!x||!x.authenticated||!x.user||x.user.role!=='owner')return true;css();owner.querySelectorAll('.tabs').forEach(x=>x.classList.add('od-hide'));const d=document.createElement('div');d.id='ownerDashboard';d.className='card';d.innerHTML=`<div class="od-head"><div><h2 style="margin:0">🏢 Profil agence / propriétaire</h2><p class="muted" style="margin:5px 0">Espace professionnel LOGEO pour gérer vos annonces et rechercher des biens.</p></div></div><div id="odProfile" class="card od-profile" style="margin:12px 0 0"></div><div class="od-nav"><button onclick="odShow('ownerExtendedForm')">➕<br>Créer une annonce</button><button class="od-ct" onclick="location.href='/owner/market'">🔎<br>ChercherTrouver</button><button onclick="odShow('odListings')">📢<br>Mes annonces</button><button onclick="odShow('odApps')">👥<br>Candidatures</button></div></div>`;owner.insertBefore(d,owner.firstChild);const p=document.getElementById('odProfile');p.innerHTML=`<b>👤 ${esc(x.user.name||'Propriétaire')}</b><br><span class="muted">${esc(x.user.email||'')} · Compte propriétaire / agence</span>`;return true}
window.odShow=function(id){const f=document.getElementById(id);if(!f)return;document.getElementById('ownerExtendedForm')?.classList.add('od-hide');document.getElementById('odListings')?.classList.add('od-hide');document.getElementById('odApps')?.classList.add('od-hide');f.classList.remove('od-hide');f.scrollIntoView({behavior:'smooth',block:'start'})};
function boot(){build().then(ok=>{if(!ok)setTimeout(boot,300)})}if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',boot);else boot();
})();</script>'''
        response.set_data(page.replace('</body>',script+'</body>'))
    except Exception:
        pass
    return response
