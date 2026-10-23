from flask import Flask, request, jsonify, session, send_from_directory, send_file
import os, hashlib, tempfile, time
from threading import Lock
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
 if USE_PG:
  c.execute('''CREATE TABLE IF NOT EXISTS users(id SERIAL PRIMARY KEY,email TEXT UNIQUE NOT NULL,password_hash TEXT NOT NULL,name TEXT,city TEXT,budget DOUBLE PRECISION,type TEXT,min_surface DOUBLE PRECISION,max_distance DOUBLE PRECISION,furnished TEXT,move_date TEXT,school TEXT,role TEXT DEFAULT 'student',created_at TEXT NOT NULL)''');c.execute('''CREATE TABLE IF NOT EXISTS listings(id SERIAL PRIMARY KEY,title TEXT NOT NULL,city TEXT NOT NULL,price DOUBLE PRECISION NOT NULL,surface DOUBLE PRECISION,type TEXT,distance_km DOUBLE PRECISION,furnished INTEGER,available_date TEXT,source TEXT,source_url TEXT UNIQUE,description TEXT,owner_id INTEGER,created_at TEXT NOT NULL)''');c.execute('''CREATE TABLE IF NOT EXISTS favorites(user_id INTEGER,listing_id INTEGER,PRIMARY KEY(user_id,listing_id))''');c.execute('''CREATE TABLE IF NOT EXISTS applications(user_id INTEGER,listing_id INTEGER,status TEXT DEFAULT 'sent',created_at TEXT NOT NULL,PRIMARY KEY(user_id,listing_id))''')
 else:c.executescript('''CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY AUTOINCREMENT,email TEXT UNIQUE NOT NULL,password_hash TEXT NOT NULL,name TEXT,city TEXT,budget REAL,type TEXT,min_surface REAL,max_distance REAL,furnished TEXT,move_date TEXT,school TEXT,role TEXT DEFAULT 'student',created_at TEXT NOT NULL);CREATE TABLE IF NOT EXISTS listings(id INTEGER PRIMARY KEY AUTOINCREMENT,title TEXT NOT NULL,city TEXT NOT NULL,price REAL NOT NULL,surface REAL,type TEXT,distance_km REAL,furnished INTEGER,available_date TEXT,source TEXT,source_url TEXT UNIQUE,description TEXT,owner_id INTEGER,created_at TEXT NOT NULL);CREATE TABLE IF NOT EXISTS favorites(user_id INTEGER,listing_id INTEGER,PRIMARY KEY(user_id,listing_id));CREATE TABLE IF NOT EXISTS applications(user_id INTEGER,listing_id INTEGER,status TEXT DEFAULT 'sent',created_at TEXT NOT NULL,PRIMARY KEY(user_id,listing_id));''')
 c.commit();c.close()
init()
def hp(p):return hashlib.sha256(p.encode()).hexdigest()
def user():
 if 'uid' not in session:return None
 c=db();u=c.execute(ph('SELECT * FROM users WHERE id=?'),(session['uid'],)).fetchone();c.close();return u
def require_user():
 u=user(); return (u,None) if u else (None,(jsonify(error='Authentification requise'),401))
@app.route('/')
def home(): return send_from_directory('static','index.html')
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
@app.post('/api/profile')
def profile():
 u,e=require_user()
 if e:return e
 x=request.json or {};fields=['name','city','budget','type','min_surface','max_distance','furnished','move_date','school'];sets=[];vals=[]
 for f in fields:
  if f in x:sets.append(f+'=?');vals.append(x[f] if x[f] != '' else None)
 c=db()
 if sets:c.execute(ph('UPDATE users SET '+','.join(sets)+' WHERE id=?'),(*vals,u['id']));c.commit()
 c.close();return jsonify(ok=True)
@app.get('/api/matches')
def matches():
 u,e=require_user()
 if e:return e
 c=db();rows=c.execute(ph('SELECT * FROM listings ORDER BY created_at DESC')).fetchall();fav={r['listing_id'] for r in c.execute(ph('SELECT listing_id FROM favorites WHERE user_id=?'),(u['id'],)).fetchall()};apps={r['listing_id'] for r in c.execute(ph('SELECT listing_id FROM applications WHERE user_id=?'),(u['id'],)).fetchall()};c.close();out=[]
 for r in rows:
  d=dict(r);score=50;reasons=[]
  if u['city'] and d.get('city','').lower()==str(u['city']).lower():score+=25;reasons.append('Ville souhaitée')
  if u['budget'] is not None and d.get('price') is not None:
   if float(d['price'])<=float(u['budget']):score+=15;reasons.append('Dans le budget')
   else:score-=20
  if u['type'] and d.get('type')==u['type']:score+=10;reasons.append('Type recherché')
  if u['min_surface'] and d.get('surface') and float(d['surface'])>=float(u['min_surface']):score+=5;reasons.append('Surface suffisante')
  d.update(score=max(0,min(100,score)),reasons=reasons,favorite=d['id'] in fav,application=d['id'] in apps);out.append(d)
 return jsonify(listings=out)
@app.get('/api/search')
def search():
 u,e=require_user()
 if e:return e
 q=(request.args.get('q') or '').lower().strip();city=(request.args.get('city') or '').lower().strip();typ=request.args.get('type') or '';price=request.args.get('price');surface=request.args.get('surface');rooms=request.args.get('rooms')
 c=db();rows=c.execute(ph('SELECT * FROM listings ORDER BY created_at DESC')).fetchall();c.close();out=[]
 for r in rows:
  d=dict(r);text=' '.join(str(d.get(k) or '') for k in ('title','city','description','type')).lower()
  if q and q not in text:continue
  if city and city not in str(d.get('city') or '').lower():continue
  if typ and typ.lower() not in str(d.get('type') or '').lower():continue
  if price and float(d.get('price') or 0)>float(price):continue
  if surface and float(d.get('surface') or 0)<float(surface):continue
  if rooms and str(d.get('rooms') or '')!=rooms:continue
  d['photo']=d.get('photo')
  out.append(d)
 return jsonify(listings=out)
@app.get('/api/owner/listings')
def owner_listings():
 u,e=require_user()
 if e:return e
 c=db();rows=c.execute(ph('SELECT * FROM listings WHERE owner_id=? ORDER BY created_at DESC'),(u['id'],)).fetchall();c.close();return jsonify(listings=[dict(r) for r in rows])
@app.post('/api/listings')
def create_listing():
 u,e=require_user()
 if e:return e
 x=request.json or {};required=['title','city','price','surface','type']
 if any(x.get(k) in (None,'') for k in required):return jsonify(error='Titre, ville, prix, surface et type requis'),400
 c=db();cur=c.execute(ph('INSERT INTO listings(title,city,price,surface,type,distance_km,furnished,available_date,source,source_url,description,owner_id,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)'),(x['title'],x['city'],float(x['price']),float(x['surface']),x['type'],float(x.get('distance_km',0)),1 if x.get('furnished') in (True,'yes','Oui',1,'1') else 0,x.get('available_date'),x.get('source','owner'),x.get('source_url'),x.get('description',''),u['id'],datetime.utcnow().isoformat()));c.commit();lid=cur.lastrowid;c.close();return jsonify(ok=True,id=lid)
@app.patch('/api/owner/listings/<int:listing_id>')
def owner_update(listing_id):
 u,e=require_user()
 if e:return e
 x=request.json or {};allowed=['title','city','price','surface','type','description'];sets=[];vals=[]
 for f in allowed:
  if f in x:sets.append(f+'=?');vals.append(x[f])
 if not sets:return jsonify(error='Aucune modification'),400
 c=db();c.execute(ph('UPDATE listings SET '+','.join(sets)+' WHERE id=? AND owner_id=?'),(*vals,listing_id,u['id']));c.commit();c.close();return jsonify(ok=True)
@app.delete('/api/owner/listings/<int:listing_id>')
def owner_delete(listing_id):
 u,e=require_user()
 if e:return e
 c=db();c.execute(ph('DELETE FROM listings WHERE id=? AND owner_id=?'),(listing_id,u['id']));c.commit();c.close();return jsonify(ok=True)
@app.route('/owner/market')
def owner_market():return send_from_directory('static','index.html')

VIDEO_LAST_REQUEST = {}
VIDEO_RATE_LOCK = Lock()

@app.post('/api/generate-video')
def generate_video_api():
    client_ip = request.remote_addr or 'unknown'
    now = time.time()
    with VIDEO_RATE_LOCK:
        last = VIDEO_LAST_REQUEST.get(client_ip, 0)
        if now - last < 60:
            return jsonify(error='Pour préserver le quota gratuit, attendez une minute entre deux générations.'), 429
        VIDEO_LAST_REQUEST[client_ip] = now
        if len(VIDEO_LAST_REQUEST) > 1000:
            VIDEO_LAST_REQUEST.clear()
            VIDEO_LAST_REQUEST[client_ip] = now
    if request.content_length and request.content_length > 13 * 1024 * 1024:
        return jsonify(error='Fichier trop volumineux (12 Mo maximum).'), 413
    upload = request.files.get('photo')
    prompt = (request.form.get('prompt') or '').strip()
    mode = (request.form.get('mode') or 'natural').strip()
    if not upload or not upload.filename:
        return jsonify(error='Ajoutez une photo.'), 400
    if request.form.get('rights') != 'yes':
        return jsonify(error='Confirmez vos droits et le consentement nécessaire.'), 400
    if mode == 'adult':
        return jsonify(error='Le mode adulte reste désactivé tant que le moteur et ses règles ne sont pas validés.'), 400
    if not prompt or len(prompt) > 1000:
        return jsonify(error='Décrivez le mouvement (1 000 caractères maximum).'), 400
    ext = os.path.splitext(upload.filename)[1].lower()
    if ext not in ('.jpg', '.jpeg', '.png', '.webp'):
        return jsonify(error='Format accepté : JPG, PNG ou WEBP.'), 400
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(prefix='motion-input-', suffix=ext, delete=False) as temp:
            temp_path = temp.name
            upload.save(temp)
        # La photo est transmise à un Space public tiers pour effectuer le calcul.
        from gradio_client import Client, handle_file
        seconds = 5.0 if request.form.get('duration') == '5' else 3.0
        # Le modèle suit généralement mieux les consignes de mouvement en anglais.
        # Traduction automatique gratuite, avec repli sur le texte original si indisponible.
        try:
            from deep_translator import GoogleTranslator
            action_prompt = GoogleTranslator(source='auto', target='en').translate(prompt) or prompt
        except Exception:
            action_prompt = prompt
        motion_prompt = (
            "IMAGE-TO-VIDEO ANIMATION. Animate the actual person, not the camera. "
            "Required physical action: " + action_prompt + ". "
            "The person must visibly and continuously perform this exact action with their own "
            "arms, hands, head, face, and torso as relevant. Show clear body movement from the "
            "first second to the last second. Preserve the person's identity and the background. "
            "Locked-off static camera, no zoom, no pan, no camera movement. "
            "Do not replace body movement with camera movement."
        )
        # Moteur principal, puis moteur de secours public si le premier est saturé.
        # Les Spaces publics restent soumis à des quotas et peuvent changer d'API.
        engines = [
            ('r3gm/wan2-2-fp8da-aoti-preview2', 'primary'),
            ('preSalesAIAutomation/imagetovideo', 'fallback'),
        ]
        last_error = None
        video_path = None
        for space_id, engine_kind in engines:
            try:
                engine = Client(space_id, hf_token=os.environ.get('HF_TOKEN') or None)
                if engine_kind == 'primary':
                    result = engine.predict(
                        handle_file(temp_path), None, motion_prompt, 4, "",
                        seconds, 1, 1, 42, True, 5, "UniPCMultistep", 6.0, 16,
                        False, True, api_name='/generate_video'
                    )
                else:
                    # API alternative Wan 2.2 : image, prompt, steps, negative prompt,
                    # durée, deux guidances, seed et option seed aléatoire.
                    result = engine.predict(
                        handle_file(temp_path), motion_prompt, 4, "",
                        seconds, 1, 1, 42, True, api_name='/generate_video_sync'
                    )
                candidate = result[0] if isinstance(result, (list, tuple)) else result
                if isinstance(candidate, dict):
                    candidate = candidate.get('path') or candidate.get('name') or candidate.get('video')
                if candidate and os.path.isfile(str(candidate)):
                    video_path = str(candidate)
                    app.logger.info('Génération vidéo réussie via %s', space_id)
                    break
                last_error = RuntimeError('Le moteur n’a pas renvoyé de fichier vidéo local.')
            except Exception as engine_exc:
                last_error = engine_exc
                app.logger.warning('Moteur vidéo %s indisponible : %s', space_id, str(engine_exc)[:200])
        if not video_path:
            raise RuntimeError('Tous les moteurs vidéo sont indisponibles') from last_error
        return send_file(video_path, mimetype='video/mp4', as_attachment=True, download_name='motion-studio.mp4')
    except Exception as exc:
        app.logger.warning('Échec de génération vidéo : %s: %s', type(exc).__name__, str(exc)[:300])
        return jsonify(error='Le moteur gratuit est occupé ou indisponible. Réessayez plus tard.'), 503
    finally:
        if temp_path:
            try:
                os.remove(temp_path)
            except OSError:
                pass


IMAGE_LAST_REQUEST = {}
IMAGE_RATE_LOCK = Lock()


@app.post('/api/video-face-swap')
def video_face_swap_api():
    """Face swap vidéo via MuAPI ; la clé reste côté serveur."""
    api_key = os.environ.get('MUAPI_API_KEY')
    if not api_key:
        return jsonify(error="Le moteur Face Swap n'est pas configuré : ajoutez MUAPI_API_KEY dans les variables d'environnement de l'hébergement."), 503
    if request.content_length and request.content_length > 22 * 1024 * 1024:
        return jsonify(error="Fichiers trop volumineux. La vidéo doit faire moins de 10 Mo et la photo moins de 10 Mo."), 413
    face = request.files.get('photo')
    video = request.files.get('target_video')
    if not face or not face.filename or not video or not video.filename:
        return jsonify(error="Ajoutez une photo du visage et la vidéo à modifier."), 400
    if request.form.get('rights') != 'yes':
        return jsonify(error="Confirmez le consentement explicite de la personne dont le visage sera utilisé et vos droits sur la vidéo."), 400
    face_ext = os.path.splitext(face.filename)[1].lower()
    video_ext = os.path.splitext(video.filename)[1].lower()
    if face_ext not in ('.jpg', '.jpeg', '.png', '.webp'):
        return jsonify(error="La photo doit être au format JPG, PNG ou WEBP."), 400
    if video_ext not in ('.mp4', '.mov', '.webm'):
        return jsonify(error="La vidéo doit être au format MP4, MOV ou WEBM."), 400
    face_path = video_path = None
    try:
        import requests
        with tempfile.NamedTemporaryFile(prefix='face-source-', suffix=face_ext, delete=False) as f:
            face_path = f.name
            face.save(f)
        with tempfile.NamedTemporaryFile(prefix='face-target-', suffix=video_ext, delete=False) as f:
            video_path = f.name
            video.save(f)
        if os.path.getsize(face_path) > 10 * 1024 * 1024:
            return jsonify(error="La photo doit faire 10 Mo maximum."), 413
        if os.path.getsize(video_path) >= 10 * 1024 * 1024:
            return jsonify(error="La vidéo doit faire moins de 10 Mo pour le moteur Face Swap."), 413
        headers = {'x-api-key': api_key}
        api = 'https://api.muapi.ai/api/v1'
        # MuAPI héberge temporairement les fichiers ; leurs URLs sont utilisées uniquement pour le job.
        with open(face_path, 'rb') as f:
            up_face = requests.post(api + '/upload_file', headers=headers, files={'file': (os.path.basename(face_path), f)}, timeout=60)
        with open(video_path, 'rb') as f:
            up_video = requests.post(api + '/upload_file', headers=headers, files={'file': (os.path.basename(video_path), f)}, timeout=90)
        if not up_face.ok or not up_video.ok:
            app.logger.warning('MuAPI upload failed: face=%s video=%s', up_face.status_code, up_video.status_code)
            return jsonify(error="Impossible de transmettre les fichiers au moteur. Vérifiez le solde et la clé MuAPI."), 502
        face_url = up_face.json().get('url')
        video_url = up_video.json().get('url')
        if not face_url or not video_url:
            return jsonify(error="Le service de dépôt n'a pas fourni les liens nécessaires."), 502
        submitted = requests.post(api + '/ai-video-face-swap', headers={**headers, 'Content-Type':'application/json'},
            json={'image_url': face_url, 'video_url': video_url, 'target_index': 0, 'target_gender': 'All'}, timeout=60)
        if not submitted.ok:
            app.logger.warning('MuAPI submit failed: %s %s', submitted.status_code, submitted.text[:300])
            return jsonify(error="Le moteur a refusé la demande. Vérifiez les limites vidéo et votre solde MuAPI."), 502
        request_id = submitted.json().get('request_id')
        if not request_id:
            return jsonify(error="Le moteur n'a pas renvoyé de numéro de traitement."), 502
        # Polling borné pour ne pas monopoliser le serveur indéfiniment.
        deadline = time.time() + 240
        while time.time() < deadline:
            poll = requests.get(api + '/predictions/' + str(request_id) + '/result', headers=headers, timeout=30)
            if not poll.ok:
                app.logger.warning('MuAPI polling failed: %s', poll.status_code)
                return jsonify(error="Impossible de récupérer le résultat auprès du moteur."), 502
            result = poll.json()
            state = result.get('status')
            if state == 'completed':
                outputs = result.get('outputs') or result.get('output')
                if isinstance(outputs, dict):
                    out_url = outputs.get('video') or outputs.get('url') or outputs.get('video_url')
                elif isinstance(outputs, list):
                    out_url = outputs[0] if outputs else None
                else:
                    out_url = outputs
                if isinstance(out_url, dict):
                    out_url = out_url.get('url') or out_url.get('video')
                if not isinstance(out_url, str) or not out_url.startswith('https://'):
                    return jsonify(error="Le moteur a terminé sans fournir de lien vidéo exploitable."), 502
                media = requests.get(out_url, timeout=120)
                media.raise_for_status()
                return send_file(__import__('io').BytesIO(media.content), mimetype='video/mp4', as_attachment=True, download_name='motion-studio-face-swap.mp4')
            if state in ('failed', 'cancelled'):
                app.logger.warning('MuAPI job failed: %s', str(result.get('error'))[:300])
                return jsonify(error="Le moteur n'a pas pu traiter cette vidéo. Vérifiez la qualité du visage et les limites du fichier."), 502
            time.sleep(4)
        return jsonify(error="Le traitement prend trop de temps. Réessayez avec une vidéo plus courte."), 504
    except Exception as exc:
        app.logger.warning('Face swap API error: %s: %s', type(exc).__name__, str(exc)[:300])
        return jsonify(error="Erreur lors du traitement Face Swap. Vérifiez la configuration MuAPI et réessayez."), 503
    finally:
        for path in (face_path, video_path):
            if path:
                try: os.remove(path)
                except OSError: pass

@app.post('/api/transform-image')
def transform_image_api():
    """Édition d'image via le Space public FLUX.2 Klein 4B sur Hugging Face."""
    client_ip = request.remote_addr or 'unknown'
    now = time.time()
    with IMAGE_RATE_LOCK:
        last = IMAGE_LAST_REQUEST.get(client_ip, 0)
        if now - last < 60:
            return jsonify(error='Pour préserver le quota partagé, attendez une minute entre deux transformations.'), 429
        IMAGE_LAST_REQUEST[client_ip] = now

    if request.content_length and request.content_length > 13 * 1024 * 1024:
        return jsonify(error='Fichier trop volumineux (12 Mo maximum).'), 413
    upload = request.files.get('photo')
    prompt = (request.form.get('prompt') or '').strip()
    if not upload or not upload.filename:
        return jsonify(error='Ajoutez une photo.'), 400
    if request.form.get('rights') != 'yes':
        return jsonify(error='Confirmez vos droits et le consentement nécessaire.'), 400
    if not prompt or len(prompt) > 1000:
        return jsonify(error='Décrivez la transformation (1 000 caractères maximum).'), 400
    ext = os.path.splitext(upload.filename)[1].lower()
    if ext not in ('.jpg', '.jpeg', '.png', '.webp'):
        return jsonify(error='Format accepté : JPG, PNG ou WEBP.'), 400

    temp_path = output_path = None
    try:
        from gradio_client import Client, handle_file
        with tempfile.NamedTemporaryFile(prefix='motion-input-', suffix=ext, delete=False) as temp:
            temp_path = temp.name
            upload.save(temp)

        # Espace public partagé : aucun jeton payant requis, mais file d'attente et quotas possibles.
        client = Client('black-forest-labs/FLUX.2-klein-4B', hf_token=os.environ.get('HF_TOKEN') or None)
        result = client.predict(
            prompt,
            [(handle_file(temp_path), None)],
            'Distilled (4 steps)',
            42,
            True,
            1024,
            1024,
            4,
            1.0,
            False,
            api_name='/infer'
        )
        candidate = result[0] if isinstance(result, (list, tuple)) else result
        if isinstance(candidate, dict):
            candidate = candidate.get('path') or candidate.get('name') or candidate.get('url')
        if not candidate:
            return jsonify(error='Le moteur photo n’a pas renvoyé d’image exploitable.'), 502
        candidate = str(candidate)
        if os.path.isfile(candidate):
            output_path = candidate
            return send_file(output_path, mimetype='image/png', as_attachment=True,
                             download_name='motion-studio-transformee.png')
        if candidate.startswith('https://'):
            import requests
            response = requests.get(candidate, timeout=90)
            response.raise_for_status()
            return send_file(__import__('io').BytesIO(response.content), mimetype='image/png',
                             as_attachment=True, download_name='motion-studio-transformee.png')
        return jsonify(error='Le moteur photo a renvoyé un format de résultat inattendu.'), 502
    except Exception as exc:
        app.logger.warning('FLUX.2 Klein image edit failed: %s: %s', type(exc).__name__, str(exc)[:250])
        return jsonify(error='Le moteur photo gratuit est occupé, a atteint son quota ou a refusé cette consigne. Réessayez plus tard avec une transformation autorisée.'), 503
    finally:
        if temp_path:
            try: os.remove(temp_path)
            except OSError: pass


if __name__=='__main__':serve(app,host='0.0.0.0',port=int(os.environ.get('PORT','8080')))