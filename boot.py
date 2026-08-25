import os
from app import app
import owner_import
import advanced_import
from waitress import serve

serve(app, host='0.0.0.0', port=int(os.environ.get('PORT','5000')))
