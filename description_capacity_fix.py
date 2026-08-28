import app as logeo

# PostgreSQL TEXT is unbounded for practical listing descriptions.
# Force the column to TEXT so a future VARCHAR(500)-style migration cannot
# silently truncate imported descriptions. SQLite already accepts TEXT.
def _ensure_description_capacity():
    c = logeo.db()
    try:
        if getattr(logeo, 'USE_PG', False):
            c.execute('ALTER TABLE listings ALTER COLUMN description TYPE TEXT')
        else:
            # SQLite TEXT has no fixed character limit; nothing to alter.
            pass
        c.commit()
        print('LOGEO: description storage capacity = TEXT/unlimited')
    except Exception as exc:
        try: c.rollback()
        except Exception: pass
        print(f'LOGEO: description capacity check failed: {exc}')
    finally:
        c.close()

_ensure_description_capacity()
