from flask import redirect
import app as logeo

# Compatibility entry point: both URL forms are accepted.
@logeo.app.get('/owner/market/')
def owner_market_trailing_slash():
    return redirect('/owner/market', code=302)
