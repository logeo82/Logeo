from flask import Flask, request, jsonify, session, send_from_directory
import os, csv, io, hashlib
from datetime import datetime, timedelta
from waitress import serve
DATABASE_URL=os.environ.get('DATABASE_URL'); USE_PG=bool(DATABASE_URL)
if USE_PG:
 import psycopg
 from psycopg.rows import dict_row
else: import sqlite3
BASE=os.path.dirname(__file__); DATA_DIR=os.environ.get('LOGEO_DATA_DIR','/data'); DB=os.path.join(DATA_DIR,'logeo.db')
if not USE_PG:
 try: os.makedirs(DATA_DIR,exist_ok=True)
 except OSError: DATA_DIR=BASE; DB=os.path.join(DATA_DIR,'logeo.db')
app=Flask(__name__,static_folder='static'); app.secret_key=os.environ.get('LOGEO_SECRET','logeo-session-secret-v1'); app.config.update(SESSION_COOKIE_HTTPONLY=True,SESSION_COOKIE_SAMESITE='Lax',SESSION_COOKIE_SECURE=False,PERMANENT_SESSION_LIFETIME=timedelta(days=30))
def db():
 if USE_PG:return psycopg.connect(DATABASE_URL,row_factory=dict_row)
 c=sqlite3.connect(DB);c.row_factory=sqlite3.Row;return c
def ph(sql):return sql.replace('?','%s') if USE_PG else sql
def init():
 c=db()
 if USE_PG:c.execute('''CREATE TABLE IF NOT EXISTS users(id SERIAL PRIMARY KEY,email TEXT UNIQUE NOT NULL,password_hash TEXT NOT NULL,name TEXT,city TEXT,budget DOUBLE PRECISION,type TEXT,min_surface DOUBLE PRECISION,max_distance DOUBLE PRECISION,furnished TEXT,move_date TEXT,school TEXT,role TEXT DEFAULT 'student',created_at TEXT NOT NULL)''');c.execute('''CREATE TABLE IF NOT EXISTS listings(id SERIAL PRIMARY KEY,title TEXT NOT NULL,city TEXT NOT NULL,price DOUBLE PRECISION NOT NULL,surface DOUBLE PRECISION,type TEXT,distance_km DOUBLE PRECISION,furnished INTEGER,available_date TEXT,source TEXT,source_url TEXT UNIQUE,description TEXT,owner_id INTEGER,created_at TEXT NOT NULL)''');c.execute('''CREATE TABLE IF NOT EXISTS favorites(user_id INTEGER,listing_id INTEGER,PRIMARY KEY(user_id,listing_id))''');c.execute('''CREATE TABLE IF NOT EXISTS applications(user_id INTEGER,listing_id INTEGER,status TEXT DEFAULT 'sent',created_at TEXT NOT NULL,PRIMARY KEY(user_id,listing_id))''')
 else:c.executescript('''CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY AUTOINCREMENT,email TEXT UNIQUE NOT NULL,password_hash TEXT NOT NULL,name TEXT,city TEXT,budget REAL,type TEXT,min_surface REAL,max_distance REAL,furnished TEXT,move_date TEXT,school TEXT,role TEXT DEFAULT 'student',created_at TEXT NOT NULL);CREATE TABLE IF NOT EXISTS listings(id INTEGER PRIMARY KEY AUTOINCREMENT,title TEXT NOT NULL,city TEXT NOT NULL,price REAL NOT NULL,surface REAL,type TEXT,distance_km REAL,furnished INTEGER,available_date TEXT,source TEXT,source_url TEXT UNIQUE,description TEXT,owner_id INTEGER,created_at TEXT NOT NULL);CREATE TABLE IF NOT EXISTS favorites(user_id INTEGER,listing_id INTEGER,PRIMARY KEY(user_id,listing_id));CREATE TABLE IF NOT EXISTS applications(user_id INTEGER,listing_id INTEGER,status TEXT DEFAULT 'sent',created_at TEXT NOT NULL,PRIMARY KEY(user_id,listing_id));''')
 c.commit();c.close()
init()
def hp(p):return hashlib.sha256(p.encode()).hexdigest()
def user():
 if 'uid' not in session:return None
 c=db();u=c.execute(ph('SELECT * FROM users WHERE id=?'),(session['uid'],)).fetchone();c.close();return u
@app.route('/')
def home(): return open(os.path.join(BASE,'static','index.html'),encoding='utf-8').read()
@app.get('/api/health')
def health():return jsonify(ok=True)
@app.post('/api/register')
def register():
 x=request.json or {};email=x.get('email','').lower().strip();password=x.get('password','');role=x.get('role','student')
 if not email or not password:return jsonify(error='Email et mot de passe requis'),400
 c=db()
 try:
  if USE_PG:uid=c.execute(ph('INSERT INTO users(email,password_hash,name,role,created_at) VALUES(?,?,?,?,?) RETURNING id'),(email,hp(password),x.get('name',''),role,datetime.utcnow().isoformat())).fetchone()['id']
  else:uid=c.execute(ph('INSERT INTO users(email,password_hash,name,role,created_at) VALUES(?,?,?,?,?)'),(email,hp(password),x.get('name',''),role,datetime.utcnow().isoformat())).lastrowid
  c.commit();session['uid']=uid;session.permanent=True
 except Exception:c.rollback();c.close();return jsonify(error='Compte déjà existant'),409
 c.close();return jsonify(ok=True)
@app.post('/api/login')
def login():
 x=request.json or {};c=db();u=c.execute(ph('SELECT * FROM users WHERE email=? AND password_hash=?'),(x.get('email','').lower().strip(),hp(x.get('password','')))).fetchone();c.close()
 if not u:return jsonify(error='Identifiants incorrects'),401
 session['uid']=u['id'];session.permanent=True;return jsonify(ok=True,user=dict(u))
@app.post('/api/logout')
def logout():session.clear();return jsonify(ok=True)
@app.get('/api/me')
def me():
 u=user();return jsonify(authenticated=bool(u),user=dict(u) if u else None)

def require_user():
 u=user()
 if not u:return None, (jsonify(error='Authentification requise'),401)
 return u,None

@app.post('/api/profile')
def profile():
 u,e=require_user()
 if e:return e
 x=request.json or {}; fields=['name','city','budget','type','min_surface','max_distance','furnished','move_date','school']; c=db()
 sets=[]; vals=[]
 for f in fields:
  if f in x: sets.append(f+'=?'); vals.append(x[f] if x[f] != '' else None)
 if sets:c.execute(ph('UPDATE users SET '+','.join(sets)+' WHERE id=?'),(*vals,u['id']));c.commit()
 c.close();return jsonify(ok=True)

@app.get('/api/matches')
def matches():
 u,e=require_user()
 if e:return e
 c=db(); rows=c.execute(ph('SELECT * FROM listings ORDER BY created_at DESC')).fetchall(); fav={r['listing_id'] for r in c.execute(ph('SELECT listing_id FROM favorites WHERE user_id=?'),(u['id'],)).fetchall()}; apps={r['listing_id'] for r in c.execute(ph('SELECT listing_id FROM applications WHERE user_id=?'),(u['id'],)).fetchall()};c.close()
 out=[]
 for r in rows:
  d=dict(r); score=50; reasons=[]
  if u['city'] and d.get('city','').lower()==str(u['city']).lower(): score+=25;reasons.append('Ville souhaitée')
  if u['budget'] is not None and d.get('price') is not None:
   if float(d['price'])<=float(u['budget']): score+=15;reasons.append('Dans le budget')
   else: score-=20
  if u['type'] and d.get('type')==u['type']: score+=10;reasons.append('Type recherché')
  if u['min_surface'] and d.get('surface') and float(d['surface'])>=float(u['min_surface']): score+=5;reasons.append('Surface suffisante')
  d.update(score=max(0,min(100,score)),reasons=reasons,favorite=d['id'] in fav,application=d['id'] in apps)
  out.append(d)
 return jsonify(listings=out)

@app.get('/api/owner/listings')
def owner_listings():
 u,e=require_user()
 if e:return e
 c=db();rows=c.execute(ph('SELECT * FROM listings WHERE owner_id=? ORDER BY created_at DESC'),(u['id'],)).fetchall();c.close();return jsonify(listings=[dict(r) for r in rows])

@app.patch('/api/owner/listings/<int:listing_id>')
def owner_update(listing_id):
 u,e=require_user()
 if e:return e
 x=request.json or {}; allowed=['title','city','price','surface','type','rooms','description'];sets=[];vals=[]
 c=db()
 for f in allowed:
  if f in x:sets.append(f+'=?');vals.append(x[f])
 if not sets:return jsonify(error='Aucune modification'),400
 vals.append(listing_id);vals.append(u['id']);c.execute(ph('UPDATE listings SET '+','.join(sets)+' WHERE id=? AND owner_id=?'),tuple(vals));c.commit();c.close();return jsonify(ok=True)

@app.delete('/api/owner/listings/<int:listing_id>')
def owner_delete(listing_id):
 u,e=require_user()
 if e:return e
 c=db();c.execute(ph('DELETE FROM listings WHERE id=? AND owner_id=?'),(listing_id,u['id']));c.commit();c.close();return jsonify(ok=True)

@app.post('/api/listings')
def create_listing():
 u,e=require_user()
 if e:return e
 x=request.json or {};required=['title','city','price','surface','type']
 if any(x.get(k) in (None,'') for k in required):return jsonify(error='Titre, ville, prix, surface et type requis'),400
 c=db();cur=c.execute(ph('INSERT INTO listings(title,city,price,surface,type,distance_km,furnished,available_date,source,source_url,description,owner_id,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)'),(x['title'],x['city'],float(x['price']),float(x['surface']),x['type'],float(x.get('distance_km',0)),1 if x.get('furnished') in (True,'yes','Oui',1,'1') else 0,x.get('available_date'),x.get('source','owner'),x.get('source_url'),x.get('description',''),u['id'],datetime.utcnow().isoformat()));c.commit();lid=cur.lastrowid if not USE_PG else None;c.close();return jsonify(ok=True,id=lid)

@app.route('/owner/market')
def owner_market(): return send_from_directory(BASE,'static','index.html')
if __name__=='__main__': serve(app,host='0.0.0.0',port=int(os.environ.get('PORT','8080')))
