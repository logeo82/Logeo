from flask import Flask, request, jsonify, session, send_from_directory
import sqlite3, os, csv, io, hashlib
from datetime import datetime
BASE=os.path.dirname(__file__); DB=os.path.join(BASE,'logeo.db')
app=Flask(__name__,static_folder='static'); app.secret_key=os.environ.get('LOGEO_SECRET','change-this-secret')
def db():
 c=sqlite3.connect(DB); c.row_factory=sqlite3.Row; return c
def init():
 c=db(); c.executescript('''CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY AUTOINCREMENT,email TEXT UNIQUE NOT NULL,password_hash TEXT NOT NULL,name TEXT,city TEXT,budget REAL,type TEXT,min_surface REAL,max_distance REAL,furnished TEXT,move_date TEXT,school TEXT,created_at TEXT NOT NULL); CREATE TABLE IF NOT EXISTS listings(id INTEGER PRIMARY KEY AUTOINCREMENT,title TEXT NOT NULL,city TEXT NOT NULL,price REAL NOT NULL,surface REAL,type TEXT,distance_km REAL,furnished INTEGER,available_date TEXT,source TEXT,source_url TEXT UNIQUE,description TEXT,created_at TEXT NOT NULL); CREATE TABLE IF NOT EXISTS favorites(user_id INTEGER,listing_id INTEGER,PRIMARY KEY(user_id,listing_id)); CREATE TABLE IF NOT EXISTS applications(user_id INTEGER,listing_id INTEGER,status TEXT DEFAULT 'sent',created_at TEXT NOT NULL,PRIMARY KEY(user_id,listing_id));''')
 if c.execute('SELECT COUNT(*) n FROM listings').fetchone()['n']==0:
  rows=[('Studio centre-ville','Montauban',590,21,'Studio',1.4,1,'2026-09-01','demo','demo-1','Lumineux, proche transports'),('T1 proche établissements','Montauban',625,25,'T1',2.1,1,'2026-08-28','demo','demo-2','Calme, parking'),('Studio rénové','Montauban',650,19,'Studio',3.8,0,'2026-09-05','demo','demo-3','Rénové et lumineux'),('T2 avec balcon','Montauban',690,39,'T2',4.2,1,'2026-09-01','demo','demo-4','Balcon, résidence calme')]
  c.executemany('INSERT INTO listings(title,city,price,surface,type,distance_km,furnished,available_date,source,source_url,description,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',[r+(datetime.utcnow().isoformat(),) for r in rows])
 c.commit(); c.close()
init()
def hp(p): return hashlib.sha256(p.encode()).hexdigest()
def user():
 if 'uid' not in session:return None
 c=db(); u=c.execute('SELECT * FROM users WHERE id=?',(session['uid'],)).fetchone(); c.close(); return u
@app.route('/')
def home(): return send_from_directory('static','index.html')
@app.post('/api/register')
def register():
 x=request.json or {}
 if not x.get('email') or not x.get('password'): return jsonify(error='Email et mot de passe requis'),400
 c=db()
 try:
  cur=c.execute('INSERT INTO users(email,password_hash,name,created_at) VALUES(?,?,?,?)',(x['email'].lower().strip(),hp(x['password']),x.get('name',''),datetime.utcnow().isoformat())); c.commit(); session['uid']=cur.lastrowid
 except sqlite3.IntegrityError:return jsonify(error='Compte déjà existant'),409
 finally:c.close()
 return jsonify(ok=True)
@app.post('/api/login')
def login():
 x=request.json or {}; c=db(); u=c.execute('SELECT * FROM users WHERE email=? AND password_hash=?',(x.get('email','').lower().strip(),hp(x.get('password','')))).fetchone(); c.close()
 if not u:return jsonify(error='Identifiants incorrects'),401
 session['uid']=u['id']; return jsonify(ok=True)
@app.post('/api/logout')
def logout(): session.clear(); return jsonify(ok=True)
@app.get('/api/me')
def me():
 u=user(); return jsonify(authenticated=bool(u),user=dict(u) if u else None)
@app.post('/api/profile')
def profile():
 u=user()
 if not u:return jsonify(error='Connexion requise'),401
 x=request.json or {}; fields=['name','city','budget','type','min_surface','max_distance','furnished','move_date','school']; vals=[x.get(k) for k in fields]
 c=db(); c.execute('UPDATE users SET '+','.join(f'{k}=?' for k in fields)+' WHERE id=?',vals+[u['id']]); c.commit(); c.close(); return jsonify(ok=True)
def score(l,u):
 city=(u['city'] or '').strip().lower()
 if l['city'].strip().lower()!=city:return 0,['Ville différente']
 budget=u['budget'] or 0; ms=u['min_surface'] or 0; md=u['max_distance'] or 999
 if budget and l['price']>budget:return 0,['Budget dépassé']
 if md and l['distance_km']>md:return 0,['Trop éloigné']
 if ms and l['surface']<ms:return 0,['Surface insuffisante']
 if u['furnished'] in ('yes','no') and l['furnished']!=(1 if u['furnished']=='yes' else 0):return 0,['Meublé/non-meublé incompatible']
 budget_s=100 if not budget else max(0,100-(l['price']/budget-.65)*285)
 dist_s=100 if not md else max(0,100-(l['distance_km']/md)*55)
 surf_s=100 if not ms else min(100,70+(l['surface']-ms)*4)
 type_s=100 if l['type']==u['type'] else (75 if u['type']=='T1' and l['type']=='Studio' else 45)
 date_s=100
 if u['move_date'] and l['available_date']:
  d=(datetime.fromisoformat(l['available_date'])-datetime.fromisoformat(u['move_date'])).days; date_s=100 if d<=0 else max(0,100-d*3)
 total=round(.25*budget_s+.20*dist_s+.10*date_s+.15*type_s+.10*surf_s+.10*100+.10*90)
 return min(100,total),['Très forte correspondance' if total>=90 else 'Bonne correspondance' if total>=75 else 'Correspondance moyenne']
@app.get('/api/matches')
def matches():
 u=user()
 if not u:return jsonify(error='Connexion requise'),401
 c=db(); rows=c.execute('SELECT * FROM listings ORDER BY id DESC').fetchall(); fav={r['listing_id'] for r in c.execute('SELECT listing_id FROM favorites WHERE user_id=?',(u['id'],))}; apps={r['listing_id']:r['status'] for r in c.execute('SELECT listing_id,status FROM applications WHERE user_id=?',(u['id'],))}; c.close(); out=[]
 for l in rows:
  s,w=score(l,u)
  if s: out.append({**dict(l),'score':s,'reasons':w,'favorite':l['id'] in fav,'application':apps.get(l['id'])})
 out.sort(key=lambda x:(x['score'],-x['price']),reverse=True); return jsonify(listings=out)
@app.post('/api/favorite/<int:lid>')
def favorite(lid):
 u=user()
 if not u:return jsonify(error='Connexion requise'),401
 c=db(); ex=c.execute('SELECT 1 FROM favorites WHERE user_id=? AND listing_id=?',(u['id'],lid)).fetchone()
 if ex:c.execute('DELETE FROM favorites WHERE user_id=? AND listing_id=?',(u['id'],lid)); state=False
 else:c.execute('INSERT OR IGNORE INTO favorites VALUES(?,?)',(u['id'],lid)); state=True
 c.commit();c.close();return jsonify(favorite=state)
@app.post('/api/application/<int:lid>')
def application(lid):
 u=user()
 if not u:return jsonify(error='Connexion requise'),401
 c=db();c.execute('INSERT OR REPLACE INTO applications VALUES(?,?,?,?)',(u['id'],lid,'sent',datetime.utcnow().isoformat()));c.commit();c.close();return jsonify(ok=True)
@app.get('/api/applications')
def applications():
 u=user()
 if not u:return jsonify(error='Connexion requise'),401
 c=db();r=c.execute('SELECT a.status,l.* FROM applications a JOIN listings l ON l.id=a.listing_id WHERE a.user_id=? ORDER BY a.created_at DESC',(u['id'],)).fetchall();c.close();return jsonify(applications=[dict(x) for x in r])
@app.post('/api/admin/import')
def import_csv():
 if request.headers.get('X-Admin-Token')!=os.environ.get('LOGEO_ADMIN_TOKEN','dev-admin'):return jsonify(error='Admin non autorisé'),403
 raw=request.files.get('file')
 if not raw:return jsonify(error='CSV manquant'),400
 reader=csv.DictReader(io.StringIO(raw.read().decode('utf-8-sig')));c=db();count=0
 for r in reader:
  try:c.execute('INSERT OR IGNORE INTO listings(title,city,price,surface,type,distance_km,furnished,available_date,source,source_url,description,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',(r['title'],r['city'],float(r['price']),float(r.get('surface') or 0),r.get('type',''),float(r.get('distance_km') or 0),1 if str(r.get('furnished','')).lower() in ('1','true','yes','oui') else 0,r.get('available_date'),r.get('source','import'),r.get('source_url'),r.get('description',''),datetime.utcnow().isoformat()));count+=1
  except Exception:pass
 c.commit();c.close();return jsonify(imported=count)
if __name__=='__main__': app.run(host='0.0.0.0',port=int(os.environ.get('PORT',5000)))
