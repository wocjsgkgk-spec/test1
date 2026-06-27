from pathlib import Path

from app.main import create_app

def test_taskflow_page_uses_todo_api_and_mobile_layout() -> None:
    page = (Path(__file__).parent / "static" / "index.html").read_text(
        encoding="utf-8"
    )

    assert 'const API_ROOT = "/todos"' in page
    assert 'method: "POST"' in page
    assert '/toggle' in page
    assert 'method: "DELETE"' in page
    assert "@media (max-width: 760px)" in page
    assert "complete-fade" in page
    assert "showRecommendations" in page
    assert "오늘의 첫 흐름을 시작해 볼까요?" in page
    assert 'id="auth-form"' in page
    assert 'authenticate("/login")' in page
    assert 'authenticate("/signup")' in page
    assert 'localStorage.setItem(TOKEN_KEY, token)' in page
    assert 'Authorization: `Bearer ${token}`' in page
    assert 'id="logout-button"' in page


def test_app_mounts_taskflow_static_page() -> None:
    app = create_app()

    assert any(route.path == "" and route.name == "taskflow-static" for route in app.routes)


def test_playwright_ui_test_is_present() -> None:
    test_file = Path(__file__).parent / "e2e" / "taskflow-ui.e2e.js"

    assert test_file.is_file()
    assert "textDecorationLine" in test_file.read_text(encoding="utf-8")
