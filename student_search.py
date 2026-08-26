import json
import app as logeo

@logeo.app.get('/api/student/search')
def student_search():
    u=logeo.user()
    if not u or u['role']!='student':
        return logeo.jsonify(error='Connexion étudiant requise'),403
    args=logeo.request.args
    city=(args.get('city') or '').strip().lower()
    q=(args.get('q') or '').strip().lower()
    typ=(args.get('type') or 'all').strip()
    max_price=float(args.get('max_price') or 0)
    min_surface=float(args.get('min_surface') or 0)
    furnished=args.get('furnished','all')
    c=logeo.db()
    rows=c.execute('SELECT * FROM listings ORDER BY id DESC').fetchall()
    fav={r['listing_id'] for r in c.execute('SELECT listing_id FROM favorites WHERE user_id=?',(u['id'],))}
    apps={r['listing_id']:r['status'] for r in c.execute('SELECT listing_id,status FROM applications WHERE user_id=?',(u['id'],))}
    c.close()
    out=[]
    for l in rows:
        d=dict(l)
        hay=' '.join(str(d.get(k) or '') for k in ('title','city','description','type','neighborhood')).lower()
        if city and city not in str(d.get('city') or '').lower(): continue
        if q and q not in hay: continue
        if typ!='all' and typ and d.get('type')!=typ: continue
        if max_price and float(d.get('price') or 0)>max_price: continue
        if min_surface and float(d.get('surface') or 0)<min_surface: continue
        if furnished!='all' and bool(d.get('furnished')) != (furnished=='yes'): continue
        # Keep compatibility as a ranking signal, but do not use it to hide valid search results.
        try: score,reasons=logeo.score(d,u)
        except Exception: score,reasons=0,[]
        d.update(score=score,reasons=reasons,favorite=d['id'] in fav,application=apps.get(d['id']))
        out.append(d)
    sort=args.get('sort','score')
    if sort=='price': out.sort(key=lambda x: float(x.get('price') or 0))
    elif sort=='surface': out.sort(key=lambda x: float(x.get('surface') or 0), reverse=True)
    else: out.sort(key=lambda x: (float(x.get('score') or 0),-float(x.get('price') or 0)), reverse=True)
    return logeo.jsonify(listings=out,total=len(out))
