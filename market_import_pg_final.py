import market_import as mi

_INT_FLAGS = {
    'furnished','parking','garage','balcony','terrace','garden','cellar',
    'elevator','air_conditioning','double_glazing','internet_fiber','pool','exclusive'
}

def _flag(v):
    if isinstance(v, bool):
        return 1 if v else 0
    if v is None or v == '':
        return v
    if isinstance(v, (int, float)):
        return int(v)
    s = str(v).strip().lower()
    if s in ('true','1','yes','oui','on'):
        return 1
    if s in ('false','0','no','non','off'):
        return 0
    return v

def _normalise(obj):
    if not isinstance(obj, dict):
        return obj
    out = dict(obj)
    for k in _INT_FLAGS:
        if k in out:
            out[k] = _flag(out[k])
    return out

_old_payload = mi._payload
def _payload_safe(item, source, external):
    return _normalise(_old_payload(_normalise(item), source, external))
mi._payload = _payload_safe

_old_update = mi._update_existing
def _update_safe(c, existing, payload):
    return _old_update(c, existing, _normalise(payload))
mi._update_existing = _update_safe

# owner_extended already normalises on insert; wrap it too so every CT path is safe.
try:
    import owner_extended as oe
    _old_insert = oe._insert
    def _insert_safe(x, u):
        return _old_insert(_normalise(x), u)
    oe._insert = _insert_safe
except Exception as exc:
    print(f'LOGEO: owner insert normalization unavailable: {exc}')

print('LOGEO: FINAL PostgreSQL boolean->integer normalization enabled')
