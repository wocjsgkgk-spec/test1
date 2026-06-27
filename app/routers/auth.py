from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db import get_session
from app.models.auth import Credentials, TokenResponse
from app.models.user import User
from app.services.auth import (
    create_access_token,
    hash_password,
    normalize_email,
    verify_password,
)

router = APIRouter()


@router.post(
    "/signup",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
)
async def signup(
    payload: Credentials,
    session: Annotated[Session, Depends(get_session)],
) -> TokenResponse:
    email = normalize_email(payload.email)
    user = User(email=email, password_hash=hash_password(payload.password))
    try:
        session.add(user)
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="이미 가입된 이메일입니다",
        ) from exc
    return TokenResponse(access_token=create_access_token(user.id))


@router.post("/login", response_model=TokenResponse)
async def login(
    payload: Credentials,
    session: Annotated[Session, Depends(get_session)],
) -> TokenResponse:
    email = normalize_email(payload.email)
    user = session.query(User).filter_by(email=email).one_or_none()

    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="이메일 또는 비밀번호가 올바르지 않습니다",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return TokenResponse(access_token=create_access_token(user.id))
