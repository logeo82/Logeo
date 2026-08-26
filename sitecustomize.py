"""Railway startup hooks for LOGEO.

Railway starts `waitress-serve app:app`, so boot.py is intentionally bypassed.
Import the feature modules that boot.py normally registers, then install the
PostgreSQL-safe student profile handler before requests are served.
"""

import app as logeo
from flask import request, jsonify

# These imports register routes/UI hooks on the existing Flask application.
for _module in (
    "owner_import",
    "advanced_import",
    "owner_extended",
    "listing_route",
    "seloger_import_v2",
    "market_search",
    "market_import",
    "owner_dashboard",
    "student_ui",
    "student_search",
):
    try:
        __import__(_module)
    except Exception as exc:
        print(f"LOGEO optional module {_module} disabled: {exc}")


@logeo.app.before_request
def _postgres_profile_fix():
    # app.py's legacy profile route used SQLite '?' placeholders directly.
    # Under psycopg PostgreSQL needs '%s'. Handle this endpoint here so the
    # working authentication/application code remains untouched.
    if request.path != "/api/profile" or request.method != "POST":
        return None
    u = logeo.user()
    if not u:
        return jsonify(error="Connexion requise"), 401
    if u["role"] != "student":
        return jsonify(error="Profil étudiant uniquement"), 403
    x = request.get_json(silent=True) or {}
    fields = ["name", "city", "budget", "type", "min_surface", "max_distance", "furnished", "move_date", "school"]
    vals = [x.get(k) for k in fields]
    c = logeo.db()
    try:
        sql = "UPDATE users SET " + ",".join(f"{k}=?" for k in fields) + " WHERE id=?"
        c.execute(logeo.ph(sql), vals + [u["id"]])
        c.commit()
    finally:
        c.close()
    return jsonify(ok=True)
