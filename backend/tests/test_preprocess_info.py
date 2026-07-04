from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_preprocess_info_exposes_algorithm_metadata():
    r = client.get("/api/preprocess-image/info")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body.get("algorithm") == "binary_scribble_v3_famicom"
    assert body.get("max_edge") == 512
    assert isinstance(body.get("tips"), list)
    req = body.get("requirements") or {}
    assert "image/jpeg" in (req.get("input") or {}).get("mime_types", [])
    assert (req.get("preprocess_output") or {}).get("format") == "PNG"
    assert (req.get("character_output") or {}).get("format") == "PNG"
