import os
from flask import Response, request, jsonify
import app as logeo
from app import app

# Core/legacy modules are kept for backward compatibility. The free internal
# LOGEO AI Engine is loaded before the final market connector.
for _module in ("owner_import","advanced_import","owner_extended","listing_route","seloger_import_v2","market_import","enrich_endpoint_fix","listing_enrichment","listing_enrichment_fix","listing_local_parse","market_reference_ui","owner_dashboard","student_ui","student_search","bridge_import","description_refresh","market_import_pg_fix","market_import_final","description_capacity_fix","market_import_pg_final","logeo_ai_engine","market_search"):
    try:
        __import__(_module)
        print(f"LOGEO module loaded: {_module}")
    except Exception as exc:
        print(f"LOGEO module disabled: {_module}: {exc}")

from waitress import serve
serve(app,host='0.0.0.0',port=int(os.environ.get('PORT','8080')))
