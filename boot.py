import os
from app import app
import owner_import
import advanced_import
import owner_extended
import seloger_import_v2
try:
    import market_search
    import market_import
except Exception as e:
    print('LOGEO market search/import disabled:', e)
from waitress import serve

serve(app, host='0.0.0.0', port=int(os.environ.get('PORT','5000')))
