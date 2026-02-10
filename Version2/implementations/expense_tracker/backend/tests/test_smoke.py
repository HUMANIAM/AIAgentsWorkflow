from backend.app import ingest_selection

def test_ingest_selection_smoke():
    out = ingest_selection('hello')
    assert out['ok'] is True
    assert out['text'] == 'hello'
