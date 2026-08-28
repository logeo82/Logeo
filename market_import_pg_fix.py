import market_import as mi

# PostgreSQL stores feature flags as INTEGER. ChercherTrouver can return
# JSON booleans, so normalize them before updating an existing listing.
_INT_FIELDS = {
    'furnished','parking','garage','balcony','terrace','garden','cellar',
    'elevator','air_conditioning','double_glazing','internet_fiber','pool','exclusive'
}

def _as_int(value):
    if isinstance(value, bool):
        return 1 if value else 0
    if value is None or value == '':
        return value
    if isinstance(value, (int, float)):
        return int(value)
    s = str(value).strip().lower()
    if s in ('true','1','yes','oui','on'):
        return 1
    if s in ('false','0','no','non','off'):
        return 0
    return value

_original_update_existing = mi._update_existing

def _update_existing_pg_safe(c, existing, payload):
    safe = dict(payload or {})
    for field in _INT_FIELDS:
        if field in safe:
            safe[field] = _as_int(safe[field])
    return _original_update_existing(c, existing, safe)

mi._update_existing = _update_existing_pg_safe
print('LOGEO: PostgreSQL boolean/integer import fix enabled')
