from flask import jsonify
import app as logeo

@logeo.app.get('/api/owner/listings-compat')
def owner_listings_compat():
    u=logeo.require_role('owner')
    if not u:
        return jsonify(error='Connexion propriétaire requise'),401
    if u is False:
        return jsonify(error='Compte étudiant'),403
    c=logeo.db()
    try:
        own_count=c.execute('SELECT COUNT(*) n FROM listings WHERE owner_id=?',(u['id'],)).fetchone()['n']
        # Older announcements were created before owner_id existed. If this owner
        # has no listings yet, claim only those legacy/unassigned listings once.
        if own_count==0:
            legacy=c.execute('SELECT COUNT(*) n FROM listings WHERE owner_id IS NULL').fetchone()['n']
            if legacy:
                c.execute('UPDATE listings SET owner_id=? WHERE owner_id IS NULL',(u['id'],))
                c.commit()
        rows=c.execute('SELECT * FROM listings WHERE owner_id=? ORDER BY id DESC',(u['id'],)).fetchall()
        return jsonify(listings=[dict(r) for r in rows])
    finally:
        c.close()

@logeo.app.after_request
def owner_listings_compat_ui(response):
    try:
        if response.content_type and response.content_type.startswith('text/html'):
            page=response.get_data(as_text=True)
            if 'id="ownerApp"' in page and 'owner-listings-compat' not in page:
                script="""<script>(function(){function install(){if(typeof window.loadOwner==='function'&&window.loadOwner.__compat)return;window.loadOwner=async function(){var box=document.getElementById('myListings');if(!box)return;try{var r=await fetch('/api/owner/listings-compat'),x=await r.json();if(!r.ok)throw Error(x.error||'Erreur');var rows=x.listings||[];window.allMatches=rows.map(function(l){return Object.assign({},l,{score:100,reasons:[]})});box.innerHTML='<div class=\"card\"><h2>📢 Mes annonces</h2>'+(rows.length?rows.map(function(l){return '<div class=\"card\" onclick=\"openListingDetail('+l.id+')\" style=\"cursor:pointer\"><h3>'+String(l.title||'Annonce').replace(/</g,'&lt;')+'</h3><b>'+l.price+' €</b> · '+l.surface+' m² · '+String(l.type||'')+'<br><span class=\"muted\">📍 '+String(l.city||'')+'</span><p>'+String(l.description||'').slice(0,250)+'</p><button type=\"button\" class=\"secondary\" onclick=\"event.stopPropagation();openListingDetail('+l.id+')\">📄 Ouvrir l\'annonce</button></div>'}).join(''):'<p class=\"muted\">Aucune annonce</p>')+'</div>';if(typeof ownerTab==='function')ownerTab('myListings')}catch(e){box.innerHTML='<div class=\"card\"><p class=\"err\">Impossible de charger les annonces : '+e.message+'</p></div>'}};window.loadOwner.__compat=true;window.loadOwner()}if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',install);else setTimeout(install,0)})();</script>"""
                page=page.replace('</body>',script+'</body>')
                response.set_data(page)
    except Exception:
        pass
    return response
