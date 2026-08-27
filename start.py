import os
from flask import Response
from app import app

# Load all optional LOGEO modules before serving the application.
for _module in (
    "owner_import",
    "advanced_import",
    "owner_extended",
    "listing_route",
    "seloger_import_v2",
    "market_search",
    "market_import",
    "market_entry",
    "owner_dashboard",
    "student_ui",
    "student_search",
    "bridge_import",
):
    try:
        __import__(_module)
        print(f"LOGEO module loaded: {_module}")
    except Exception as exc:
        print(f"LOGEO module disabled: {_module}: {exc}")

@app.after_request
def definitive_market_entry(response):
    try:
        if not response.content_type or not response.content_type.startswith("text/html"):
            return response
        html = response.get_data(as_text=True)
        if "id=\"marketSearchDefinitive\"" in html:
            return response
        block = '''
<div id="marketSearchDefinitive" style="margin:12px 0;padding:16px;border:2px solid #111827;border-radius:14px;background:#eef2ff">
  <div style="font-size:19px;font-weight:800;margin-bottom:5px">🔎 Chercher-Trouver</div>
  <div style="color:#667085;margin-bottom:10px">Recherche automatique multi-portails et import des annonces dans LOGEO.</div>
  <a href="/owner/market" style="display:block;text-decoration:none"><button type="button" style="width:100%;padding:13px;border:0;border-radius:10px;background:#111827;color:#fff;font-weight:800;cursor:pointer">🔎 Rechercher des annonces</button></a>
</div>
'''
        marker = '<section id="ownerApp" class="hidden">'
        if marker in html:
            html = html.replace(marker, marker + block, 1)
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.set_data(html)
    except Exception as exc:
        print(f"LOGEO market UI injection error: {exc}")
    return response

from waitress import serve
serve(app, host="0.0.0.0", port=int(os.environ.get("PORT", "8080")))
