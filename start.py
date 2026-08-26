import os

from app import app

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
        print(f"LOGEO module loaded: {_module}")
    except Exception as exc:
        print(f"LOGEO module disabled: {_module}: {exc}")

@app.after_request
def force_market_entry(response):
    try:
        if response.content_type and response.content_type.startswith("text/html"):
            html = response.get_data(as_text=True)
            marker = '<section id="ownerApp" class="hidden">'
            if marker in html and 'id="forceChercherTrouver"' not in html:
                entry = '''<div id="forceChercherTrouver" style="margin:12px 0;padding:16px;border:2px solid #111827;border-radius:14px;background:#eef2ff"><div style="font-size:18px;font-weight:800;margin-bottom:6px">🔎 Chercher-Trouver</div><div style="color:#667085;margin-bottom:10px">Rechercher des annonces sur les portails immobiliers et les importer dans LOGEO.</div><a href="/owner/market" style="display:block;text-decoration:none"><button type="button" style="width:100%;padding:13px;border:0;border-radius:10px;background:#111827;color:#fff;font-weight:800;cursor:pointer">🔎 Ouvrir Chercher-Trouver</button></a></div>'''
                response.set_data(html.replace(marker, marker + entry, 1))
    except Exception as exc:
        print(f"LOGEO owner market UI injection disabled: {exc}")
    return response

from waitress import serve
serve(app, host="0.0.0.0", port=int(os.environ.get("PORT", "8080")))
