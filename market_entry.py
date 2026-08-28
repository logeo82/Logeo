from flask import redirect
import app as logeo

# Compatibility entry point: both URL forms are accepted.
@logeo.app.get('/owner/market/')
def owner_market_trailing_slash():
    return redirect('/owner/market', code=302)

# The owner dashboard replaces the original ownerApp contents in the browser.
# Add the Chercher-Trouver entry directly to that generated dashboard so it
# remains visible without altering the existing dashboard behaviour.
@logeo.app.after_request
def inject_market_dashboard_entry(response):
    try:
        if response.content_type and response.content_type.startswith('text/html'):
            html=response.get_data(as_text=True)
            script='''<script>(function(){function add(){var d=document.getElementById('ownerDashboard');if(!d){return false}if(document.getElementById('marketDashboardEntry'))return true;var head=d.querySelector('.od-head');if(!head)return false;var b=document.createElement('a');b.id='marketDashboardEntry';b.href='/owner/market';b.textContent='🔎 Chercher-Trouver';b.style.cssText='display:inline-flex;align-items:center;justify-content:center;text-decoration:none;background:#111827;color:#fff;border-radius:9px;padding:12px 16px;font-weight:700;white-space:nowrap;margin-right:8px';head.appendChild(b);return true}if(!add()){var n=0,t=setInterval(function(){if(add()||++n>40)clearInterval(t)},250)}})();</script>'''
            if '</body>' in html and 'marketDashboardEntry' not in html:
                html=html.replace('</body>',script+'</body>',1)
                response.set_data(html)
    except Exception as exc:
        print(f'LOGEO market dashboard entry error: {exc}')
    return response