import base64
import os
import time
from pathlib import Path

import jwt
import pytest
from fastapi.testclient import TestClient

from app.main import auth_secret, create_app


def token(
    username: str = "student",
    role: str = "STUDENT",
    client: str = "angular-workshop",
    exp: int | None = None,
) -> str:
    issued_at = int(time.time())
    claims = {
        "sub": username,
        "role": role,
        "client": client,
        "iat": issued_at,
        "exp": exp if exp is not None else issued_at + 3600,
    }
    return jwt.encode(claims, os.environ["AUTH_TOKEN_SECRET"], algorithm="HS256")


def headers(username: str = "student", role: str = "STUDENT") -> dict[str, str]:
    return {"Authorization": f"Bearer {token(username, role)}"}


def test_lists_seeded_tasks(tmp_path: Path) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        response = client.get("/api/tasks", headers=headers())
    assert response.status_code == 200
    assert len(response.json()) == 2


def test_creates_task_and_summary(tmp_path: Path) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        created = client.post(
            "/api/tasks",
            headers=headers(),
            json={"title": "Add tests", "description": "Improve coverage", "status": "TODO", "priority": "HIGH"},
        )
        summary = client.get("/api/summary", headers=headers())
    assert created.status_code == 201
    assert created.json()["owner"] == "student"
    assert summary.json()["total"] == 3


def test_uploads_requirement(tmp_path: Path) -> None:
    upload_dir = tmp_path / "uploads"
    app = create_app(str(tmp_path / "workshop.db"), str(upload_dir))
    with TestClient(app) as client:
        response = client.post(
            "/api/requirements",
            headers=headers(),
            files={"file": ("requirements.txt", b"Login must be accessible", "text/plain")},
        )
    assert response.status_code == 201
    assert (upload_dir / "requirements.txt").exists()


def test_rejects_invalid_token(tmp_path: Path) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        response = client.get("/api/tasks", headers={"Authorization": "Bearer invalid"})
    assert response.status_code == 401


def test_rejects_legacy_base64_token(tmp_path: Path) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    legacy = base64.b64encode(
        f"student|STUDENT|{int(time.time()) + 3600}|WORKSHOP_SECRET_2026".encode()
    ).decode()
    with TestClient(app) as client:
        response = client.get("/api/tasks", headers={"Authorization": f"Bearer {legacy}"})
    assert response.status_code == 401


def test_rejects_tampered_jwt(tmp_path: Path) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    valid = token()
    tampered = valid[:-1] + ("A" if valid[-1] != "A" else "B")
    with TestClient(app) as client:
        response = client.get("/api/tasks", headers={"Authorization": f"Bearer {tampered}"})
    assert response.status_code == 401


def test_rejects_expired_jwt(tmp_path: Path) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    expired = token(exp=int(time.time()) - 1)
    with TestClient(app) as client:
        response = client.get("/api/tasks", headers={"Authorization": f"Bearer {expired}"})
    assert response.status_code == 401


def test_rejects_unapproved_client_claim(tmp_path: Path) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    unsupported = token(client="other-client")
    with TestClient(app) as client:
        response = client.get("/api/tasks", headers={"Authorization": f"Bearer {unsupported}"})
    assert response.status_code == 401


def test_rejects_token_missing_required_claim(tmp_path: Path) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    incomplete = jwt.encode(
        {"sub": "student", "iat": int(time.time()), "exp": int(time.time()) + 3600},
        os.environ["AUTH_TOKEN_SECRET"],
        algorithm="HS256",
    )
    with TestClient(app) as client:
        response = client.get("/api/tasks", headers={"Authorization": f"Bearer {incomplete}"})
    assert response.status_code == 401


def test_auth_secret_is_required_and_strong(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("AUTH_TOKEN_SECRET")
    with pytest.raises(RuntimeError, match="AUTH_TOKEN_SECRET"):
        auth_secret()

    monkeypatch.setenv("AUTH_TOKEN_SECRET", "short")
    with pytest.raises(RuntimeError, match="32 UTF-8 bytes"):
        auth_secret()


def test_app_does_not_start_without_auth_secret(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("AUTH_TOKEN_SECRET")
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    try:
        with pytest.raises(RuntimeError, match="AUTH_TOKEN_SECRET"):
            with TestClient(app):
                pass
    finally:
        app.state.connection.close()
