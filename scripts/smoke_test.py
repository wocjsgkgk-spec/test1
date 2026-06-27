from __future__ import annotations

import os
import sys
import time
from dataclasses import dataclass
from typing import Any
from urllib.parse import urljoin

import httpx


PASSWORD = "password123"


class SmokeTestError(Exception):
    pass


@dataclass
class SmokeTester:
    base_url: str
    client: httpx.Client

    def url(self, path: str) -> str:
        return urljoin(f"{self.base_url}/", path.lstrip("/"))

    def request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        try:
            return self.client.request(method, self.url(path), **kwargs)
        except httpx.HTTPError as exc:
            raise SmokeTestError(f"{method} {path} 요청 실패: {exc}") from exc

    def expect_status(
        self,
        response: httpx.Response,
        expected_status: int,
        label: str,
    ) -> None:
        if response.status_code != expected_status:
            body = response.text[:500]
            raise SmokeTestError(
                f"{label} 실패: HTTP {response.status_code}, expected "
                f"{expected_status}. body={body!r}"
            )

    def run(self) -> None:
        health_response = self.request("GET", "/health")
        self.expect_status(health_response, 200, "/health")

        email = f"smoke-{int(time.time())}@example.com"
        credentials = {"email": email, "password": PASSWORD}

        signup_response = self.request("POST", "/signup", json=credentials)
        self.expect_status(signup_response, 201, "회원가입")
        signup_token = signup_response.json().get("access_token")
        if not signup_token:
            raise SmokeTestError("회원가입 응답에 access_token이 없습니다.")

        login_response = self.request("POST", "/login", json=credentials)
        self.expect_status(login_response, 200, "로그인")
        login_token = login_response.json().get("access_token")
        if not login_token:
            raise SmokeTestError("로그인 응답에 access_token이 없습니다.")

        todo_response = self.request(
            "POST",
            "/todos",
            headers={"Authorization": f"Bearer {login_token}"},
            json={"title": "Smoke test todo"},
        )
        self.expect_status(todo_response, 201, "할 일 추가")
        todo = todo_response.json()
        if todo.get("title") != "Smoke test todo":
            raise SmokeTestError(f"할 일 추가 응답 title이 올바르지 않습니다: {todo!r}")


def base_url_from_args() -> str:
    if len(sys.argv) > 1:
        return sys.argv[1].rstrip("/")

    base_url = os.getenv("SMOKE_BASE_URL") or os.getenv("BASE_URL")
    if base_url:
        return base_url.rstrip("/")

    raise SmokeTestError(
        "배포 URL이 필요합니다. 예: python scripts/smoke_test.py "
        "https://example.onrender.com"
    )


def main() -> int:
    try:
        base_url = base_url_from_args()
        with httpx.Client(timeout=20, follow_redirects=True) as client:
            SmokeTester(base_url=base_url, client=client).run()
    except SmokeTestError as exc:
        print(f"SMOKE TEST FAILED: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"SMOKE TEST FAILED: 예상하지 못한 오류: {exc}", file=sys.stderr)
        return 1

    print("SMOKE TEST PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
