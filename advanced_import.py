import os, json, urllib.request
from flask import request, jsonify
import app as logeo

CT_KEY=os.environ.get('CHERCHER_TROUVER_API_KEY','').strip()
CT_BASE='https://cherchertrouver.immo/api/v1'

def _ct(path, params):
 if not CT_KEY: raise ValueError('CHERCHER_TROUVER_API_KEY est absente de Railway')
 qs='&'.join(f'{k}={urllib.parse.quote(str(v))}' for k,v in params.items() if v not in (None,''))
 req=urllib.request.Request(f'{CT_BASE}{path}?{qs}',headers={'X-Api-Key':CT_KEY,'Accept':'application/json','User-Agent':'LOGEO/1.0'})
 with urllib.request.urlopen(req,timeout=30) as r:return json.loads(r.read().decode())

@logeo.app.get('/api/market-search')
def market_search():
 try:
  u=logeo.user()
  if not u or u.get('role')!='owner':return jsonify(error='Connexion propriétaire requise'),403
  p=request.args
  params={k:p.get(k) for k in ('q','type','transaction','ville','cp','dept','region','prix_min','prix_max','surface_min','surface_max','pieces_min','chambres_min','annee_min','annee_max','dpe','ges','updated_since','created_since','sort','page','page_size')}
  params['page_size']=min(int(params.get('page_size') or 25),100)
  data=_ct('/annonces',params)
  return jsonify(ok=True,**data)
 except Exception as e:return jsonify(error=f'Recherche marché : {e}'),422

@logeo.app.get('/api/market-detail/<source>/<reference>')
def market_detail(source,reference):
 try:
  u=logeo.user()
  if not u or u.get('role')!='owner':return jsonify(error='Connexion propriétaire requise'),403
  data=_ct(f'/annonces/{source}/{urllib.parse.quote(reference,safe="")}',{})
  return jsonify(ok=True,**data)
 except Exception as e:return jsonify(error=f'Détail annonce : {e}'),422

@logeo.app.get('/api/market-ping')
def market_ping():
 try:return jsonify(ok=True,**_ct('/ping',{}))
 except Exception as e:return jsonify(ok=False,error=str(e)),422
