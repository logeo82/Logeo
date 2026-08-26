from flask import Flask, request, jsonify, session, send_from_directory
import os, csv, io, hashlib
from datetime import datetime, timedelta
from waitress import serve

DATABASE_URL=os.environ.get('DATABASE_URL')
USE_PG=bool(DATABASE_URL)
if USE_PG:
    import psycopg
    from psycopg.rows import dict_row
else:
    import sqlite3

BASE=os.path.dirname(__file__)
DATA_DIR=os.environ.get('LOGEO_DATA_DIR','/data')
if not USE_PG:
    try: os.makedirs(DATA_DIR, exist_ok=True)
    except OSError: DATA_DIR=BASE
DB=os.path.join(DATA_DIR,'logeo.db')

app=Flask(__name__,static_folder='static')
app.secret_key=os.environ.get('LOGEO_SECRET','logeo-session-secret-v1')
app.config.update(SESSION_COOKIE_HTTPONLY=True,SESSION_COOKIE_SAMESITE='Lax',SESSION_COOKIE_SECURE=False,PERMANENT_SESSION_LIFETIME=timedelta(days=30))

def db():
    if USE_PG:
        return psycopg.connect(DATABASE_URL,row_factory=dict_row)
    c=sqlite3.connect(DB); c.row_factory=sqlite3.Row; return c

def ph(sql):
    return sql.replace('?', '%s') if USE_PG else sql

def init():
    c=db();
    if USE_PG:
        c.execute('''CREATE TABLE IF NOT EXISTS users(id SERIAL PRIMARY KEY,email TEXT UNIQUE NOT NULL,password_hash TEXT NOT NULL,name TEXT,city TEXT,budget DOUBLE PRECISION,type TEXT,min_surface DOUBLE PRECISION,max_distance DOUBLE PRECISION,furnished TEXT,move_date TEXT,school TEXT,role TEXT DEFAULT 'student',created_at TEXT NOT NULL)''')
        c.execute('''CREATE TABLE IF NOT EXISTS listings(id SERIAL PRIMARY KEY,title TEXT NOT NULL,city TEXT NOT NULL,price DOUBLE PRECISION NOT NULL,surface DOUBLE PRECISION,type TEXT,distance_km DOUBLE PRECISION,furnished INTEGER,available_date TEXT,source TEXT,source_url TEXT UNIQUE,description TEXT,owner_id INTEGER,created_at TEXT NOT NULL)''')
        c.execute('''CREATE TABLE IF NOT EXISTS favorites(user_id INTEGER,listing_id INTEGER,PRIMARY KEY(user_id,listing_id))''')
        c.execute('''CREATE TABLE IF NOT EXISTS applications(user_id INTEGER,listing_id INTEGER,status TEXT DEFAULT 'sent',created_at TEXT NOT NULL,PRIMARY KEY(user_id,listing_id))''')
    else:
        c.executescript('''CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY AUTOINCREMENT,email TEXT UNIQUE NOT NULL,password_hash TEXT NOT NULL,name TEXT,city TEXT,budget REAL,type TEXT,min_surface REAL,max_distance REAL,furnished TEXT,move_date TEXT,school TEXT,role TEXT DEFAULT 'student',created_at TEXT NOT NULL); CREATE TABLE IF NOT EXISTS listings(id INTEGER PRIMARY KEY AUTOINCREMENT,title TEXT NOT NULL,city TEXT NOT NULL,price REAL NOT NULL,surface REAL,type TEXT,distance_km REAL,furnished INTEGER,available_date TEXT,source TEXT,source_url TEXT UNIQUE,description TEXT,owner_id INTEGER,created_at TEXT NOT NULL); CREATE TABLE IF NOT EXISTS favorites(user_id INTEGER,listing_id INTEGER,PRIMARY KEY(user_id,listing_id)); CREATE TABLE IF NOT EXISTS applications(user_id INTEGER,listing_id INTEGER,status TEXT DEFAULT 'sent',created_at TEXT NOT NULL,PRIMARY KEY(user_id,listing_id));''')
    c.commit(); c.close()
init()

def hp(p): return hashlib.sha256(p.encode()).hexdigest()
def q(sql,*args):
    c=db(); r=c.execute(ph(sql),args); return c,r

def user():
    if 'uid' not in session:return None
    c=db(); u=c.execute(ph('SELECT * FROM users WHERE id=?'),(session['uid'],)).fetchone(); c.close(); return u

def require_role(role):
    u=user(); return None if not u else (u if u['role']==role else False)

@app.route('/')
def home():
    html=open(os.path.join(BASE,'static','index.html'),encoding='utf-8').read()
    inject='''<style>.listing-modal-open{overflow:hidden}.listing-detail-backdrop{position:fixed;inset:0;background:#0008}.listing-detail-panel{position:fixed;inset:3vh 4vw;background:#fff;border-radius:20px;overflow:auto;z-index:9999;box-shadow:0 20px 70px #0006}.listing-detail-close{position:absolute;right:14px;top:12px;width:44px;height:44px;border-radius:50%;font-size:28px;z-index:3}.listing-gallery{display:grid;grid-template-columns:2fr 1fr 1fr;grid-auto-rows:150px;gap:6px;background:#eef1f5}.listing-photo{background:linear-gradient(135deg,#dce2ea,#f7f8fa);display:flex;align-items:center;justify-content:center;flex-direction:column;color:#667085}.listing-photo-main{grid-row:span 2}.listing-photo span{font-size:30px}.listing-photo small{margin-top:5px}.listing-detail-body{max-width:900px;margin:auto;padding:24px}.listing-detail-score{font-size:20px;font-weight:800}.listing-detail-body h1{font-size:30px;margin:8px 0}.listing-detail-price{font-size:27px;font-weight:800}.listing-detail-price span{font-size:15px;font-weight:500}.listing-detail-location{color:#667085;margin:8px 0 18px}.listing-detail-stats{display:grid;grid-template-columns:repeat(4,1fr);border:1px solid #e4e7ec;border-radius:14px;overflow:hidden;margin:18px 0}.listing-detail-stats div{padding:14px;border-right:1px solid #e4e7ec}.listing-detail-stats div:last-child{border:0}.listing-detail-stats b,.listing-detail-stats span{display:block}.listing-detail-stats span{color:#667085;font-size:13px;margin-top:3px}.listing-mini-map{height:150px;border-radius:14px;background:#eef2f6;display:flex;align-items:center;justify-content:center;color:#667085}.listing-detail-actions{position:sticky;bottom:0;background:#fff;padding:14px 0;border-top:1px solid #eee;margin-top:20px}@media(max-width:650px){.listing-detail-panel{inset:0;border-radius:0}.listing-gallery{grid-template-columns:1fr 1fr;grid-auto-rows:105px}.listing-photo-main{grid-column:span 2;grid-row:span 2}.listing-detail-body{padding:18px}.listing-detail-body h1{font-size:24px}.listing-detail-stats{grid-template-columns:1fr 1fr}.listing-detail-stats div:nth-child(2){border-right:0}.listing-detail-stats div:nth-child(-n+2){border-bottom:1px solid #e4e7ec}}</style><script>window.allMatches=allMatches;</script><script src="/static/detail.js"></script>'''
    html=html.replace('</body>',inject+'</body>')
    html=html.replace("let role='student',allMatches=[],logeoMap,logeoMarkers=[];", "let role='student',allMatches=[],logeoMap,logeoMarkers=[];window.allMatches=allMatches;")
    html=html.replace("<div class='card'><div class='score ${l.score>=85?'green':l.score>=70?'orange':''}'>${l.score}% compatible</div><h2>${l.title}</h2>", "<div class='card' onclick='openListingDetail(${l.id})' style='cursor:pointer'><div class='score ${l.score>=85?'green':l.score>=70?'orange':''}'>${l.score}% compatible</div><h2>${l.title}</h2>")
    html=html.replace("allMatches=x.listings;renderFiltered()", "allMatches=x.listings;window.allMatches=allMatches;renderFiltered()")
    return html

@app.post('/api/register')
def register():
    x=request.json or {}; email=x.get('email','').lower().strip(); password=x.get('password',''); role=x.get('role','student')
    if not email or not password:return jsonify(error='Email et mot de passe requis'),400
    if role not in ('student','owner'):return jsonify(error='Type de compte invalide'),400
    c=db()
    try:
        if USE_PG:
            cur=c.execute(ph('INSERT INTO users(email,password_hash,name,role,created_at) VALUES(?,?,?,?,?) RETURNING id'),(email,hp(password),x.get('name',''),role,datetime.utcnow().isoformat())); uid=cur.fetchone()['id']
        else:
            cur=c.execute(ph('INSERT INTO users(email,password_hash,name,role,created_at) VALUES(?,?,?,?,?)'),(email,hp(password),x.get('name',''),role,datetime.utcnow().isoformat())); uid=cur.lastrowid
        c.commit();session['uid']=uid;session.permanent=True
    except Exception as e:
        c.rollback(); c.close(); return jsonify(error='Compte déjà existant' if 'unique' in str(e).lower() else 'Erreur création compte'),409
    c.close(); return jsonify(ok=True)

@app.post('/api/login')
def login():
    x=request.json or {}; email=x.get('email','').lower().strip(); password=x.get('password',''); c=db();u=c.execute(ph('SELECT * FROM users WHERE email=? AND password_hash=?'),(email,hp(password))).fetchone();c.close()
    if not u:return jsonify(error='Identifiants incorrects'),401
    session['uid']=u['id'];session.permanent=True;return jsonify(ok=True)

@app.post('/api/logout')
def logout():session.clear();return jsonify(ok=True)
@app.get('/api/me')
def me():
    u=user();return jsonify(authenticated=bool(u),user=dict(u) if u else None)

@app.post('/api/profile')
def profile():
    u=user()
    if not u:return jsonify(error='Connexion requise'),401
    if u['role']!='student':return jsonify(error='Profil étudiant uniquement'),403
    x=request.json or {};fields=['name','city','budget','type','min_surface','max_distance','furnished','move_date','school'];vals=[x.get(k) for k in fields];c=db();c.execute(ph('UPDATE users SET '+','.join(f'{k}=?' for k in fields)+' WHERE id=?'),vals+[u['id']]);c.commit();c.close();return jsonify(ok=True)

def score(l,u):
    city=(u['city'] or '').strip().lower()
    if l['city'].strip().lower()!=city:return 0,['Ville différente']
    budget=u['budget'] or 0;ms=u['min_surface'] or 0;md=u['max_distance'] or 999
    if budget and l['price']>budget:return 0,['Budget dépassé']
    if md and l['distance_km']>md:return 0,['Trop éloigné']
    if ms and l['surface']<ms:return 0,['Surface insuffisante']
    if u['furnished'] in ('yes','no') and l['furnished']!=(1 if u['furnished']=='yes' else 0):return 0,['Meublé/non-meublé incompatible']
    budget_s=100 if not budget else max(0,100-(l['price']/budget-.65)*285);dist_s=100 if not md else max(0,100-(l['distance_km']/md)*55);surf_s=100 if not ms else min(100,70+(l['surface']-ms)*4);type_s=100 if l['type']==u['type'] else (75 if u['type']=='T1' and l['type']=='Studio' else 45);date_s=100
    if u['move_date'] and l['available_date']:
        d=(datetime.fromisoformat(l['available_date'])-datetime.fromisoformat(u['move_date'])).days;date_s=100 if d<=0 else max(0,100-d*3)
    total=round(.25*budget_s+.20*dist_s+.10*date_s+.15*type_s+.10*surf_s+.10*100+.10*90);return min(100,total),['Très forte correspondance' if total>=90 else 'Bonne correspondance' if total>=75 else 'Correspondance moyenne']

@app.get('/api/matches')
def matches():
    u=user()
    if not u:return jsonify(error='Connexion requise'),401
    if u['role']!='student':return jsonify(error='Compte propriétaire'),403
    c=db();rows=c.execute('SELECT * FROM listings ORDER BY id DESC').fetchall();fav={r['listing_id'] for r in c.execute(ph('SELECT listing_id FROM favorites WHERE user_id=?'),(u['id'],))};apps={r['listing_id']:r['status'] for r in c.execute(ph('SELECT listing_id,status FROM applications WHERE user_id=?'),(u['id'],))};c.close();out=[]
    for l in rows:
        s,w=score(l,u)
        if s:out.append({**dict(l),'score':s,'reasons':w,'favorite':l['id'] in fav,'application':apps.get(l['id'])})
    out.sort(key=lambda x:(x['score'],-x['price']),reverse=True);return jsonify(listings=out)

@app.post('/api/favorite/<int:lid>')
def favorite(lid):
    u=user()
    if not u or u['role']!='student':return jsonify(error='Connexion étudiant requise'),403
    c=db();ex=c.execute(ph('SELECT 1 FROM favorites WHERE user_id=? AND listing_id=?'),(u['id'],lid)).fetchone()
    if ex:c.execute(ph('DELETE FROM favorites WHERE user_id=? AND listing_id=?'),(u['id'],lid));state=False
    else:c.execute(ph('INSERT INTO favorites VALUES(?,?)'),(u['id'],lid));state=True
    c.commit();c.close();return jsonify(favorite=state)

@app.post('/api/application/<int:lid>')
def application(lid):
    u=user()
    if not u or u['role']!='student':return jsonify(error='Connexion étudiant requise'),403
    c=db();c.execute(ph('INSERT INTO applications(user_id,listing_id,status,created_at) VALUES(?,?,?,?) ON CONFLICT(user_id,listing_id) DO UPDATE SET status=EXCLUDED.status'),(u['id'],lid,'sent',datetime.utcnow().isoformat())) if USE_PG else c.execute(ph('INSERT OR REPLACE INTO applications VALUES(?,?,?,?)'),(u['id'],lid,'sent',datetime.utcnow().isoformat()));c.commit();c.close();return jsonify(ok=True)

@app.get('/api/applications')
def applications():
    u=user()
    if not u or u['role']!='student':return jsonify(error='Connexion étudiant requise'),403
    c=db();r=c.execute(ph('SELECT a.status,l.* FROM applications a JOIN listings l ON l.id=a.listing_id WHERE a.user_id=? ORDER BY a.created_at DESC'),(u['id'],)).fetchall();c.close();return jsonify(applications=[dict(x) for x in r])

@app.post('/api/owner/listings')
def owner_listing():
    u=require_role('owner')
    if not u:return jsonify(error='Connexion propriétaire requise'),401
    if u is False:return jsonify(error='Compte étudiant'),403
    x=request.json or {};required=['title','city','price','surface','type']
    if any(not x.get(k) for k in required):return jsonify(error='Titre, ville, prix, surface et type sont requis'),400
    c=db();params=(x['title'],x['city'],float(x['price']),float(x['surface']),x['type'],float(x.get('distance_km') or 0),1 if str(x.get('furnished','')).lower() in ('1','true','yes','oui') else 0,x.get('available_date'),'owner',None,x.get('description',''),u['id'],datetime.utcnow().isoformat())
    if USE_PG: cur=c.execute('INSERT INTO listings(title,city,price,surface,type,distance_km,furnished,available_date,source,source_url,description,owner_id,created_at) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id',params); lid=cur.fetchone()['id']
    else: cur=c.execute(ph('INSERT INTO listings(title,city,price,surface,type,distance_km,furnished,available_date,source,source_url,description,owner_id,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)'),params);lid=cur.lastrowid
    c.commit();c.close();return jsonify(ok=True,id=lid)

@app.get('/api/owner/listings')
def owner_listings():
    u=require_role('owner')
    if not u:return jsonify(error='Connexion propriétaire requise'),401
    if u is False:return jsonify(error='Compte étudiant'),403
    c=db();r=c.execute(ph('SELECT * FROM listings WHERE owner_id=? ORDER BY id DESC'),(u['id'],)).fetchall();c.close();return jsonify(listings=[dict(x) for x in r])

@app.get('/api/owner/applications')
def owner_applications():
    u=require_role('owner')
    if not u:return jsonify(error='Connexion propriétaire requise'),401
    if u is False:return jsonify(error='Compte étudiant'),403
    c=db();r=c.execute(ph('SELECT a.status,a.created_at,l.title,l.id listing_id,u.id user_id,u.name,u.email,u.city,u.budget,u.type,u.school FROM applications a JOIN listings l ON l.id=a.listing_id JOIN users u ON u.id=a.user_id WHERE l.owner_id=? ORDER BY a.created_at DESC'),(u['id'],)).fetchall();c.close();return jsonify(applications=[dict(x) for x in r])

@app.post('/api/owner/application/<int:uid>/<int:lid>')
def owner_application(uid,lid):
    u=require_role('owner')
    if not u:return jsonify(error='Connexion propriétaire requise'),401
    if u is False:return jsonify(error='Compte étudiant'),403
    status=(request.json or {}).get('status','reviewed')
    if status not in ('reviewed','accepted','rejected'):return jsonify(error='Statut invalide'),400
    c=db();ok=c.execute(ph('SELECT 1 FROM applications a JOIN listings l ON l.id=a.listing_id WHERE a.user_id=? AND a.listing_id=? AND l.owner_id=?'),(uid,lid,u['id'])).fetchone()
    if not ok:c.close();return jsonify(error='Candidature introuvable'),404
    c.execute(ph('UPDATE applications SET status=? WHERE user_id=? AND listing_id=?'),(status,uid,lid));c.commit();c.close();return jsonify(ok=True)

@app.post('/api/admin/import')
def import_csv():
    if request.headers.get('X-Admin-Token')!=os.environ.get('LOGEO_ADMIN_TOKEN','dev-admin'):return jsonify(error='Admin non autorisé'),403
    raw=request.files.get('file')
    if not raw:return jsonify(error='CSV manquant'),400
    reader=csv.DictReader(io.StringIO(raw.read().decode('utf-8-sig')));c=db();count=0
    for r in reader:
        try:
            params=(r['title'],r['city'],float(r['price']),float(r.get('surface') or 0),r.get('type',''),float(r.get('distance_km') or 0),1 if str(r.get('furnished','')).lower() in ('1','true','yes','oui') else 0,r.get('available_date'),r.get('source','import'),r.get('source_url'),r.get('description',''),datetime.utcnow().isoformat())
            sql='INSERT INTO listings(title,city,price,surface,type,distance_km,furnished,available_date,source,source_url,description,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)' if not USE_PG else 'INSERT INTO listings(title,city,price,surface,type,distance_km,furnished,available_date,source,source_url,description,created_at) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT(source_url) DO NOTHING'
            c.execute(ph(sql),params);count+=1
        except Exception:pass
    c.commit();c.close();return jsonify(imported=count)

if __name__=='__main__':serve(app,host='0.0.0.0',port=int(os.environ.get('PORT',5000)))
