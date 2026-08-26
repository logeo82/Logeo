import app as logeo

@logeo.app.after_request
def student_listing_ui(response):
    try:
        if not (response.content_type or '').startswith('text/html'):
            return response
        page=response.get_data(as_text=True)
        if 'id="studentApp"' not in page or 'student-detail.js' in page:
            return response
        script='<script src="/static/student-detail.js?v=3"></script>'
        response.set_data(page.replace('</body>',script+'</body>'))
    except Exception:
        pass
    return response
