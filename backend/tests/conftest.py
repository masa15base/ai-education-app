"""テストでは DB に繋がずメモリへフォールバック（ローカル .env の JAWSDB を無視）。"""
import pytest


@pytest.fixture(autouse=True)
def force_memory_store(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.db.SessionLocal", None)
    monkeypatch.setattr("app.db.engine", None)
    monkeypatch.setattr("app.progress_service.SessionLocal", None)


@pytest.fixture(autouse=True)
def disable_character_vision_in_tests(monkeypatch: pytest.MonkeyPatch) -> None:
    """CI/ローカル .env の OPENAI キーで Vision を叩かない。"""
    monkeypatch.setenv("CHARACTER_VISION_ENABLED", "0")
