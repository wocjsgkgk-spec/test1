# TaskFlow API

FastAPI 기반 Todo API입니다. SQLite를 기본 개발 DB로 사용하고, `DATABASE_URL` 환경변수로 PostgreSQL 전환을 지원합니다.

## 테스트 실행

전체 테스트:

```bash
.venv/bin/pytest -q
```

핵심 백엔드 빠른 테스트:

```bash
.venv/bin/pytest test_todo_api.py test_ai_service.py test_db.py -q
```

최근 실패한 테스트만 재실행:

```bash
.venv/bin/pytest --lf -q
```

첫 실패에서 중단:

```bash
.venv/bin/pytest -x -q
```

특정 테스트만 실행:

```bash
.venv/bin/pytest test_todo_api.py::test_user_cannot_toggle_or_delete_another_users_todo -q
```

핵심 모듈(`app/routers`, `app/services`) 커버리지:

```bash
.venv/bin/pytest --cov=app.routers --cov=app.services --cov-branch --cov-report=term-missing -q
```

`--cov` 옵션을 쓰려면 `pytest-cov`가 필요합니다.

```bash
.venv/bin/pip3 install pytest-cov
```

## 저장할 때 자동으로 테스트 실행

선택 도구로 `pytest-watch`를 사용할 수 있습니다. 이 패키지는 아직 `requirements.txt`에 고정하지 않았으므로, 로컬 개발 환경에서만 필요하면 설치하세요.

```bash
.venv/bin/pip3 install pytest-watch
```

모든 변경마다 전체 테스트 실행:

```bash
.venv/bin/ptw --runner ".venv/bin/pytest -q"
```

백엔드 핵심 테스트만 반복 실행:

```bash
.venv/bin/ptw --runner ".venv/bin/pytest test_todo_api.py test_ai_service.py test_db.py -q"
```

마지막 실패 테스트만 저장할 때마다 재실행:

```bash
.venv/bin/ptw --runner ".venv/bin/pytest --lf -q"
```

특정 기능을 작업할 때는 아래처럼 관련 테스트 파일을 좁혀 실행하는 방식이 빠릅니다.

| 변경 영역 | 추천 빠른 테스트 |
|---|---|
| `app/routers/auth.py`, `app/services/auth.py`, `app/models/user.py` | `.venv/bin/pytest test_todo_api.py -q` |
| `app/routers/todos.py`, `app/orm_models.py` | `.venv/bin/pytest test_todo_api.py test_db.py -q` |
| `app/routers/recommendations.py`, `app/services/ai.py` | `.venv/bin/pytest test_ai_service.py test_todo_api.py -q` |
| `app/db.py` | `.venv/bin/pytest test_db.py test_todo_api.py -q` |
| `static/index.html` | `.venv/bin/pytest test_static_page.py -q` |
| `todo.py`, `repository.py`, `service.py`, legacy API | `.venv/bin/pytest test_todo.py test_repository.py test_api.py -q` |

`pytest-watch`는 변경 파일과 테스트의 의존관계를 자동으로 정확히 계산하지 않습니다. 대신 위 매핑처럼 작업 중인 영역에 맞는 pytest 명령을 watch runner로 지정하는 것을 권장합니다.
