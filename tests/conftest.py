import pytest


@pytest.fixture(autouse=True)
def configure_test_auth_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AUTH_TOKEN_SECRET", "test-only-shared-secret-for-hu01-tests-32-bytes")
