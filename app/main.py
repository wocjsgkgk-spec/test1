from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

load_dotenv()

from app.db import initialize_database
from app.routers.auth import router as auth_router
from app.routers.recommendations import router as recommendations_router
from app.routers.todos import router as todos_router


def create_app() -> FastAPI:
    application = FastAPI(title="할 일 API")

    @application.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    application.include_router(auth_router)
    application.include_router(todos_router)
    application.include_router(recommendations_router)
    # API 라우트 등록 후 정적 화면을 마운트해 동일한 origin에서 fetch를 처리한다.
    static_directory = Path(__file__).resolve().parent.parent / "static"
    application.mount(
        "/",
        StaticFiles(directory=static_directory, html=True),
        name="taskflow-static",
    )
    return application


initialize_database()
app = create_app()
