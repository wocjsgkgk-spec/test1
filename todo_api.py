"""기존 import 경로를 위한 호환 모듈.

새 애플리케이션 진입점은 ``app.main:app``이다.
"""

from app.db import (
    configure_database,
    configure_database_url,
    initialize_database as _initialize_database,
    reset_store,
)
from app.main import app, create_app
from app.models.auth import Credentials, CurrentUser, TokenResponse
from app.models.todo import Todo, TodoCreate
from app.routers.auth import login, signup
from app.routers.todos import (
    create_todo,
    delete_todo,
    get_todo as _get_todo,
    list_todos,
    row_to_todo as _row_to_todo,
    toggle_todo,
)
from app.services.auth import (
    base64url_decode as _base64url_decode,
    base64url_encode as _base64url_encode,
    create_access_token as _create_access_token,
    decode_access_token as _decode_access_token,
    get_current_user,
    hash_password as _hash_password,
    jwt_secret as _jwt_secret,
    normalize_email as _normalize_email,
    verify_password as _verify_password,
)

__all__ = [
    "Credentials",
    "CurrentUser",
    "Todo",
    "TodoCreate",
    "TokenResponse",
    "app",
    "configure_database",
    "configure_database_url",
    "create_app",
    "create_todo",
    "delete_todo",
    "get_current_user",
    "list_todos",
    "login",
    "reset_store",
    "signup",
    "toggle_todo",
]
