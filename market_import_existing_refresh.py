import market_import as mi
import description_refresh

# When a listing already exists, refresh its full source description instead
# of stopping at "already exists". The normal import keeps ownership/favorites
# intact; this hook only enriches the existing row after a successful upsert.
_original_import_listing = mi.import_listing

def _refresh_existing_after_import(source, reference, payload, existing=None):
    result = _original_import_listing(source, reference, payload, existing)
    try:
        listing_id = None
        if isinstance(result, dict):
            listing_id = result.get('id') or result.get('listing_id')
        if listing_id and existing:
            description_refresh._refresh_listing_description(listing_id, source, reference)
    except Exception as exc:
        print(f'LOGEO: existing listing description refresh failed: {exc}')
    return result

mi.import_listing = _refresh_existing_after_import
print('LOGEO: existing-listing full description refresh enabled')
