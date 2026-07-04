from app.security_settings import is_production_hardened


def test_production_flag_off_by_default(monkeypatch):
    monkeypatch.delenv("MANATOMO_PRODUCTION", raising=False)
    monkeypatch.delenv("ENV", raising=False)
    assert is_production_hardened() is False


def test_production_flag_manatomo(monkeypatch):
    monkeypatch.setenv("MANATOMO_PRODUCTION", "1")
    assert is_production_hardened() is True


def test_production_flag_env(monkeypatch):
    monkeypatch.delenv("MANATOMO_PRODUCTION", raising=False)
    monkeypatch.setenv("ENV", "production")
    assert is_production_hardened() is True
