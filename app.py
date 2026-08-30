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
def home():
 html=open(os.path.join(BASE,'static','index.html'),encoding='utf-8').read()
 inject='''<script>window.openLogeoMarket=function(){location.href='/owner/market'}</script>'''
 return html.replace('</body>',inject+'</body>')
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
def me():return jsonify(user=dict(user()) if user() else None)
