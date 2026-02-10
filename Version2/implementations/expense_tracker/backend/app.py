from datetime import datetime, timezone

def utc_now():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z')

def ingest_selection(text: str) -> dict:
    return {'ok': True, 'text': text.strip(), 'created_at': utc_now()}
