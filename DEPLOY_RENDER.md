# Render 배포

이 프로젝트의 추천 배포 구성은 Render Web Service + Neon PostgreSQL입니다. 앱은 Dockerfile로 실행하고, PostgreSQL은 Neon 무료 플랜에서 시작합니다.

## 1. Neon PostgreSQL 만들기

1. Neon에서 새 프로젝트를 만든다.
2. Connection string을 복사한다.
3. `DATABASE_URL` 값으로 사용할 때는 그대로 넣어도 된다. 앱이 `postgresql://`을 `postgresql+psycopg://`으로 자동 보정한다.

## 2. Render Blueprint로 서비스 만들기

1. GitHub에 이 저장소를 push한다.
2. Render에서 **New +** → **Blueprint**를 선택한다.
3. 저장소를 연결한다.
4. `render.yaml`을 감지하면 `taskflow-api` Web Service를 생성한다.

## 3. 환경변수 설정

Render 서비스의 **Environment**에서 아래 값을 설정한다.

```text
DATABASE_URL=<Neon PostgreSQL connection string>
JWT_SECRET=<자동 생성값 사용 또는 직접 입력>
OPENAI_API_KEY=<OpenAI API key>
```

`JWT_SECRET`을 직접 만들려면 로컬에서 아래 명령을 실행한다.

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

## 4. 배포 확인

배포가 끝나면 Render URL에서 아래 경로를 확인한다.

```text
https://<service-url>/docs
```

Swagger에서 `/signup`, `/login`, `/todos` 순서로 기본 동작을 확인한다.

## 5. 스모크 테스트 실행

배포 URL을 인자로 넘기면 `/health`, 회원가입, 로그인, 할 일 추가를 순서대로 확인한다.

```bash
python scripts/smoke_test.py https://<service-url>
```

환경변수로도 실행할 수 있다.

```bash
SMOKE_BASE_URL=https://<service-url> python scripts/smoke_test.py
```

실패하면 `SMOKE TEST FAILED:`로 시작하는 메시지와 함께 종료 코드 1을 반환한다.
