import hmac
import os
from datetime import datetime
from flask import request, jsonify
import app as logeo

TOKEN = os.environ.get("LOGEO_IMPORT_TOKEN", "")


def _auth():
    supplied = request.headers.get("X-Logeo-Import-Token", "")
    return bool(TOKEN) and hmac.compare_digest(supplied, TOKEN)


@logeo.app.get("/api/integrations/import-health")
def import_health():
    return jsonify(ok=True, bridge="chercher-trouver", configured=bool(TOKEN))


@logeo.app.post("/api/integrations/import-listing")
def import_listing_from_service():
    if not _auth():
        return jsonify(error="Import service unauthorized"), 401
    x = request.get_json(silent=True) or {}
    required = ("title", "city", "price", "surface", "type", "source_url")
    if any(x.get(k) in (None, "") for k in required):
        return jsonify(error="title, city, price, surface, type and source_url are required"), 400

    c = logeo.db()
    try:
        canonical = str(x["source_url"]).strip().rstrip("/")
        existing = c.execute(logeo.ph("SELECT * FROM listings WHERE source_url=?"), (canonical,)).fetchone()
        if existing:
            return jsonify(ok=True, duplicate=True, id=existing["id"], listing=dict(existing))

        owner = c.execute(logeo.ph("SELECT id FROM users WHERE role=? ORDER BY id LIMIT 1"), ("owner",)).fetchone()
        owner_id = owner["id"] if owner else None
        params = (
            str(x["title"])[:500], str(x["city"])[:200], float(x["price"]),
            float(x["surface"]), str(x["type"])[:80], float(x.get("distance_km") or 0),
            1 if str(x.get("furnished", "")).lower() in ("1", "true", "yes", "oui") else 0,
            x.get("available_date"), str(x.get("source") or "chercher-trouver")[:100],
            canonical, str(x.get("description") or "")[:10000], owner_id,
            datetime.utcnow().isoformat()
        )
        sql = "INSERT INTO listings(title,city,price,surface,type,distance_km,furnished,available_date,source,source_url,description,owner_id,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)"
        if logeo.USE_PG:
            sql = sql.replace("?", "%s") + " RETURNING id"
            listing_id = c.execute(sql, params).fetchone()["id"]
        else:
            listing_id = c.execute(sql, params).lastrowid
        c.commit()
        row = c.execute(logeo.ph("SELECT * FROM listings WHERE id=?"), (listing_id,)).fetchone()
        return jsonify(ok=True, duplicate=False, id=listing_id, listing=dict(row))
    except Exception as exc:
        c.rollback()
        return jsonify(error=f"LOGEO import failed: {type(exc).__name__}"), 500
    finally:
        c.close()
