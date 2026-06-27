import asyncio
import sqlite3
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest
from fastapi import HTTPException
from sqlalchemy import event

import app.db as db_module
from app.models.recommendation import PriorityDecision
from app.services.ai import (
    AIRecommendationError,
    AIRecommendationService,
    get_ai_service,
)
from app.services import auth as auth_service
from todo_api import app, configure_database


def request(method: str, path: str, **kwargs: object) -> httpx.Response:
    async def send_request() -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://testserver",
        ) as client:
            return await client.request(method, path, **kwargs)

    return asyncio.run(send_request())


@pytest.fixture(autouse=True)
def isolated_database(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> Path:
    monkeypatch.setenv("JWT_SECRET", "test-only-secret")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    database_path = tmp_path / "test_todos.db"
    configure_database(database_path)
    app.dependency_overrides.clear()
    yield database_path
    app.dependency_overrides.clear()


def signup(email: str = "user@example.com") -> str:
    response = request(
        "POST",
        "/signup",
        json={"email": email, "password": "password123"},
    )
    assert response.status_code == 201
    return response.json()["access_token"]


def auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_health_returns_ok() -> None:
    response = request("GET", "/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_signup_and_login_return_jwt() -> None:
    signup_response = request(
        "POST",
        "/signup",
        json={"email": "User@Example.com", "password": "password123"},
    )
    login_response = request(
        "POST",
        "/login",
        json={"email": "user@example.com", "password": "password123"},
    )

    assert signup_response.status_code == 201
    assert signup_response.json()["token_type"] == "bearer"
    assert signup_response.json()["access_token"].count(".") == 2
    assert login_response.status_code == 200
    assert login_response.json()["access_token"].count(".") == 2


def test_duplicate_signup_returns_400() -> None:
    signup()

    response = request(
        "POST",
        "/signup",
        json={"email": "user@example.com", "password": "password123"},
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "이미 가입된 이메일입니다"}


def test_signup_stores_password_as_hash(isolated_database: Path) -> None:
    signup()

    with sqlite3.connect(isolated_database) as connection:
        stored_hash, created_at = connection.execute(
            "SELECT password_hash, created_at FROM users"
        ).fetchone()

    assert stored_hash != "password123"
    assert stored_hash.startswith("scrypt$")
    assert created_at is not None


def test_login_with_wrong_password_returns_401() -> None:
    signup()

    response = request(
        "POST",
        "/login",
        json={"email": "user@example.com", "password": "wrong-password"},
    )

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


@pytest.mark.parametrize(
    ("method", "path", "kwargs"),
    [
        ("POST", "/todos", {"json": {"title": "Protected"}}),
        ("GET", "/todos", {}),
        ("PATCH", "/todos/1/toggle", {}),
        ("DELETE", "/todos/1", {}),
        ("GET", "/todos/suggest", {}),
        ("POST", "/recommendations", {}),
    ],
)
def test_todo_endpoints_without_token_return_401(
    method: str,
    path: str,
    kwargs: dict[str, object],
) -> None:
    response = request(method, path, **kwargs)

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


def test_invalid_token_returns_401() -> None:
    response = request(
        "GET",
        "/todos",
        headers=auth_headers("invalid.token.value"),
    )

    assert response.status_code == 401


def test_token_for_missing_user_returns_401() -> None:
    missing_user_token = auth_service.create_access_token(user_id=999)

    response = request(
        "GET",
        "/todos",
        headers=auth_headers(missing_user_token),
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "유효하지 않은 인증 토큰입니다"}


def test_invalid_signup_email_returns_400() -> None:
    response = request(
        "POST",
        "/signup",
        json={"email": "not-an-email", "password": "password123"},
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "올바른 이메일을 입력하세요"}


def test_password_verification_rejects_invalid_hash_formats() -> None:
    assert auth_service.verify_password("password123", "pbkdf2$salt$hash") is False
    assert auth_service.verify_password("password123", "not-a-valid-hash") is False


def test_jwt_secret_is_required(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("JWT_SECRET", raising=False)

    with pytest.raises(RuntimeError):
        auth_service.create_access_token(user_id=1)


def test_decode_access_token_rejects_bad_signature() -> None:
    token = auth_service.create_access_token(user_id=1)
    tampered_token = f"{token}x"

    with pytest.raises(HTTPException) as exc_info:
        auth_service.decode_access_token(tampered_token)

    assert exc_info.value.status_code == 401


def test_decode_access_token_rejects_expired_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(auth_service, "token_lifetime_seconds", -1)
    token = auth_service.create_access_token(user_id=1)

    with pytest.raises(HTTPException) as exc_info:
        auth_service.decode_access_token(token)

    assert exc_info.value.status_code == 401


def test_create_todo_then_list_contains_it() -> None:
    token = signup()
    create_response = request(
        "POST",
        "/todos",
        json={"title": "Write API docs", "due": "2026-06-30"},
        headers=auth_headers(token),
    )
    list_response = request("GET", "/todos", headers=auth_headers(token))

    assert create_response.status_code == 201
    assert list_response.status_code == 200
    assert list_response.json() == [
        {
            "id": 1,
            "title": "Write API docs",
            "done": False,
            "due": "2026-06-30",
        }
    ]


def test_create_todo_without_title_returns_400() -> None:
    token = signup()
    response = request(
        "POST",
        "/todos",
        json={"title": "   "},
        headers=auth_headers(token),
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "제목은 필수입니다"}


def test_toggle_missing_todo_returns_404() -> None:
    token = signup()
    response = request(
        "PATCH",
        "/todos/999/toggle",
        headers=auth_headers(token),
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "할 일을 찾을 수 없습니다"}


def test_delete_missing_todo_returns_404() -> None:
    token = signup()
    response = request(
        "DELETE",
        "/todos/999",
        headers=auth_headers(token),
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "할 일을 찾을 수 없습니다"}


def test_data_remains_after_database_reconnect(tmp_path: Path) -> None:
    database_path = tmp_path / "persistent_todos.db"
    configure_database(database_path)
    token = signup()
    request(
        "POST",
        "/todos",
        json={"title": "재시작 후에도 유지"},
        headers=auth_headers(token),
    )

    configure_database(database_path)
    response = request("GET", "/todos", headers=auth_headers(token))

    assert response.status_code == 200
    assert response.json()[0]["title"] == "재시작 후에도 유지"


def test_users_only_list_their_own_todos() -> None:
    first_token = signup("first@example.com")
    second_token = signup("second@example.com")
    request(
        "POST",
        "/todos",
        json={"title": "First user's todo"},
        headers=auth_headers(first_token),
    )
    request(
        "POST",
        "/todos",
        json={"title": "Second user's todo"},
        headers=auth_headers(second_token),
    )

    first_response = request(
        "GET",
        "/todos",
        headers=auth_headers(first_token),
    )
    second_response = request(
        "GET",
        "/todos",
        headers=auth_headers(second_token),
    )

    assert [todo["title"] for todo in first_response.json()] == ["First user's todo"]
    assert [todo["title"] for todo in second_response.json()] == ["Second user's todo"]


def test_listing_todos_uses_constant_number_of_queries() -> None:
    token = signup("owner@example.com")
    for title in ["First", "Second", "Third"]:
        request(
            "POST",
            "/todos",
            json={"title": title},
            headers=auth_headers(token),
        )

    statements = []

    def count_selects(
        _connection,
        _cursor,
        statement,
        _parameters,
        _context,
        _executemany,
    ) -> None:
        if statement.lstrip().upper().startswith("SELECT"):
            statements.append(statement)

    event.listen(db_module.engine, "before_cursor_execute", count_selects)
    try:
        response = request("GET", "/todos", headers=auth_headers(token))
    finally:
        event.remove(db_module.engine, "before_cursor_execute", count_selects)

    assert response.status_code == 200
    assert [todo["title"] for todo in response.json()] == [
        "First",
        "Second",
        "Third",
    ]
    assert len(statements) == 2


def test_created_todo_stores_current_user_id(isolated_database: Path) -> None:
    token = signup("owner@example.com")
    response = request(
        "POST",
        "/todos",
        json={"title": "Owned todo"},
        headers=auth_headers(token),
    )

    with sqlite3.connect(isolated_database) as connection:
        user_id = connection.execute(
            "SELECT user_id FROM todos WHERE id = ?",
            (response.json()["id"],),
        ).fetchone()[0]

    assert response.status_code == 201
    assert user_id == 1


def test_user_can_toggle_and_delete_own_todo() -> None:
    token = signup()
    create_response = request(
        "POST",
        "/todos",
        json={"title": "Owner can modify"},
        headers=auth_headers(token),
    )
    todo_id = create_response.json()["id"]

    toggle_response = request(
        "PATCH",
        f"/todos/{todo_id}/toggle",
        headers=auth_headers(token),
    )
    delete_response = request(
        "DELETE",
        f"/todos/{todo_id}",
        headers=auth_headers(token),
    )
    list_response = request("GET", "/todos", headers=auth_headers(token))

    assert toggle_response.status_code == 200
    assert toggle_response.json()["done"] is True
    assert delete_response.status_code == 204
    assert list_response.json() == []


def test_user_cannot_toggle_or_delete_another_users_todo() -> None:
    owner_token = signup("owner@example.com")
    other_token = signup("other@example.com")
    create_response = request(
        "POST",
        "/todos",
        json={"title": "Owner only"},
        headers=auth_headers(owner_token),
    )
    todo_id = create_response.json()["id"]

    toggle_response = request(
        "PATCH",
        f"/todos/{todo_id}/toggle",
        headers=auth_headers(other_token),
    )
    delete_response = request(
        "DELETE",
        f"/todos/{todo_id}",
        headers=auth_headers(other_token),
    )
    owner_list_response = request(
        "GET",
        "/todos",
        headers=auth_headers(owner_token),
    )

    assert toggle_response.status_code == 404
    assert delete_response.status_code == 404
    assert owner_list_response.json()[0]["done"] is False


def test_suggest_todos_returns_ai_priority_for_pending_own_todos(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    owner_token = signup("owner@example.com")
    other_token = signup("other@example.com")
    request(
        "POST",
        "/todos",
        json={"title": "Write tests", "due": "2026-06-30"},
        headers=auth_headers(owner_token),
    )
    completed_response = request(
        "POST",
        "/todos",
        json={"title": "Already done", "due": "2026-06-24"},
        headers=auth_headers(owner_token),
    )
    request(
        "PATCH",
        f"/todos/{completed_response.json()['id']}/toggle",
        headers=auth_headers(owner_token),
    )
    request(
        "POST",
        "/todos",
        json={"title": "Another user's todo", "due": "2026-06-25"},
        headers=auth_headers(other_token),
    )
    received_todos = []

    def fake_suggest_priority(todos: list) -> list:
        received_todos.extend(todos)
        return [
            {
                "title": "Write tests",
                "reason": "테스트 완료가 배포 전에 필요합니다.",
                "rank": 1,
            }
        ]

    monkeypatch.setattr(
        "app.routers.todos.ai.suggest_priority",
        fake_suggest_priority,
    )

    response = request(
        "GET",
        "/todos/suggest",
        headers=auth_headers(owner_token),
    )

    assert response.status_code == 200
    assert [todo.title for todo in received_todos] == ["Write tests"]
    assert response.json() == [
        {
            "title": "Write tests",
            "reason": "테스트 완료가 배포 전에 필요합니다.",
            "rank": 1,
        }
    ]


def test_suggest_todos_uses_due_date_fallback_when_ai_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    token = signup()
    request(
        "POST",
        "/todos",
        json={"title": "Later", "due": "2026-07-01"},
        headers=auth_headers(token),
    )
    request(
        "POST",
        "/todos",
        json={"title": "Sooner", "due": "2026-06-25"},
        headers=auth_headers(token),
    )
    failing_responses = SimpleNamespace(
        parse=lambda **kwargs: (_ for _ in ()).throw(RuntimeError("API unavailable"))
    )
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(
        "app.services.ai.OpenAI",
        lambda api_key: SimpleNamespace(responses=failing_responses),
    )

    response = request(
        "GET",
        "/todos/suggest",
        headers=auth_headers(token),
    )

    assert response.status_code == 200
    assert [item["title"] for item in response.json()] == ["Sooner", "Later"]
    assert [item["rank"] for item in response.json()] == [1, 2]


class FakeAIService(AIRecommendationService):
    def __init__(
        self,
        decisions: list[PriorityDecision] | None = None,
        error: Exception | None = None,
    ) -> None:
        self.decisions = decisions or []
        self.error = error
        self.received_todos = []
        self.call_count = 0

    async def recommend(self, todos):
        self.call_count += 1
        self.received_todos = todos
        if self.error is not None:
            raise self.error
        return self.decisions


def override_ai_service(fake_service: FakeAIService) -> None:
    async def get_fake_ai_service() -> FakeAIService:
        return fake_service

    app.dependency_overrides[get_ai_service] = get_fake_ai_service


def test_recommendations_use_only_current_users_pending_todos() -> None:
    owner_token = signup("owner@example.com")
    other_token = signup("other@example.com")
    first_response = request(
        "POST",
        "/todos",
        json={"title": "Submit report", "due": "2026-06-25"},
        headers=auth_headers(owner_token),
    )
    second_response = request(
        "POST",
        "/todos",
        json={"title": "Plan next sprint"},
        headers=auth_headers(owner_token),
    )
    completed_response = request(
        "POST",
        "/todos",
        json={"title": "Already done"},
        headers=auth_headers(owner_token),
    )
    request(
        "PATCH",
        f"/todos/{completed_response.json()['id']}/toggle",
        headers=auth_headers(owner_token),
    )
    request(
        "POST",
        "/todos",
        json={"title": "Another user's todo"},
        headers=auth_headers(other_token),
    )

    fake_service = FakeAIService(
        decisions=[
            PriorityDecision(
                todo_id=second_response.json()["id"],
                reason="다음 업무 계획을 먼저 명확히 해야 합니다.",
            ),
            PriorityDecision(
                todo_id=first_response.json()["id"],
                reason="마감일이 가까워 이어서 처리해야 합니다.",
            ),
        ]
    )
    override_ai_service(fake_service)

    response = request(
        "POST",
        "/recommendations",
        headers=auth_headers(owner_token),
    )

    assert response.status_code == 200
    assert [todo.title for todo in fake_service.received_todos] == [
        "Submit report",
        "Plan next sprint",
    ]
    assert response.json() == {
        "recommendations": [
            {
                "priority": 1,
                "todo_id": second_response.json()["id"],
                "title": "Plan next sprint",
                "due": None,
                "reason": "다음 업무 계획을 먼저 명확히 해야 합니다.",
            },
            {
                "priority": 2,
                "todo_id": first_response.json()["id"],
                "title": "Submit report",
                "due": "2026-06-25",
                "reason": "마감일이 가까워 이어서 처리해야 합니다.",
            },
        ]
    }


def test_recommendations_empty_list_skips_ai_call() -> None:
    token = signup()
    fake_service = FakeAIService()
    override_ai_service(fake_service)

    response = request(
        "POST",
        "/recommendations",
        headers=auth_headers(token),
    )

    assert response.status_code == 200
    assert response.json() == {"recommendations": []}
    assert fake_service.call_count == 0


def test_recommendations_without_api_key_return_503() -> None:
    token = signup()
    request(
        "POST",
        "/todos",
        json={"title": "Needs recommendation"},
        headers=auth_headers(token),
    )

    response = request(
        "POST",
        "/recommendations",
        headers=auth_headers(token),
    )

    assert response.status_code == 503
    assert response.json() == {"detail": "AI 추천 서비스를 사용할 수 없습니다"}


def test_recommendation_failure_returns_502() -> None:
    token = signup()
    request(
        "POST",
        "/todos",
        json={"title": "Needs recommendation"},
        headers=auth_headers(token),
    )
    fake_service = FakeAIService(error=AIRecommendationError("invalid response"))
    override_ai_service(fake_service)

    response = request(
        "POST",
        "/recommendations",
        headers=auth_headers(token),
    )

    assert response.status_code == 502
    assert response.json() == {"detail": "AI 추천을 생성하지 못했습니다"}
