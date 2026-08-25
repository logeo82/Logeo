import os, urllib.parse, urllib.request, json
from flask import jsonify
import app as logeo

BASE='https://cherchertrouver.immo/api/v1'

def _api(path, params):
    key=os.environ.get('CHERCHER_TROUVER_API_KEY','').strip()
    if not key:
        raise RuntimeError('CHERCHER_TROUVER_API_KEY absente dans Railway')
    q=urllib.parse.urlencode({k:v for k,v in params.items() if v not in (None,'')})
    url=BASE+path+('?' + q if q else '')
    req=urllib.request.Request(url,headers={'X-Api-Key':key,'Accept':'application/json','User-Agent':'LOGEO/1.0'},method='GET')
    with urllib.request.urlopen(req,timeout=15) as r:
        return json.loads(r.read().decode('utf-8'))

@logeo.app.get('/api/market-search')
def market_search():
    u=logeo.user()
    if not u or u['role']!='owner': return jsonify(error='Connexion propriétaire requise'),403
    try:
        p={k:logeo.request.args.get(k) for k in ('q','type','transaction','ville','cp','dept','region','prix_min','prix_max','surface_min','surface_max','pieces_min','chambres_min','dpe','ges','sort')}
        p['page_size']=min(int(logeo.request.args.get('page_size','10') or 10),25)
        data=_api('/annonces',p)
        return jsonify(ok=True,total=data.get('total',0),items=data.get('items',[]),next_cursor=data.get('next_cursor'))
    except Exception as e:
        return jsonify(error=f'Recherche multi-portails indisponible : {e}'),502

@logeo.app.get('/api/market-ping')
def market_ping():
    u=logeo.user()
    if not u or u['role']!='owner': return jsonify(error='Connexion propriétaire requise'),403
    try:return jsonify(ok=True,data=_api('/ping',{}))
    except Exception as e:return jsonify(ok=False,error=str(e)),502

@logeo.app.after_request
def inject_market_search(response):
    try:
        if response.content_type and response.content_type.startswith('text/html'):
            html=response.get_data(as_text=True)
            if 'id="ownerApp"' in html and '/static/market-search.js' not in html:
                html=html.replace('</body>','<script src="/static/market-search.js?v=1"></script></body>')
                response.set_data(html)
    except Exception:
        pass
    return response
