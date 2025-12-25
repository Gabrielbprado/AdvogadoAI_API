"""Authentication, profile, and template endpoints."""
from __future__ import annotations

from typing import Callable, List

from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.api.security import oauth2_scheme
from app.domain.models.user_models import (
    TemplateCreate,
    TemplateResponse,
    Token,
    UserCreate,
    UserProfile,
    UserUpdate,
)
from app.domain.services.auth_service import AuthService
from app.domain.services.user_service import UserService
from app.infrastructure.db.entities import User


def build_auth_router(
    *,
    session_factory: Callable[..., Session],
    auth_service: AuthService,
    user_service: UserService,
) -> APIRouter:
    router = APIRouter(prefix="/auth", tags=["auth"])

    def get_db():
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    async def get_current_user(
        token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
    ) -> User:
        email = auth_service.decode_token_subject(token)
        if not email:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciais inválidas")
        user = user_service.get_user_by_email(db, email)
        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuário não encontrado")
        return user

    @router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
    def register(payload: UserCreate, db: Session = Depends(get_db)) -> Token:
        existing = user_service.get_user_by_email(db, payload.email)
        if existing:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email já cadastrado")
        try:
            user = auth_service.create_user(
                db, email=payload.email, password=payload.password, full_name=payload.full_name
            )
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        token = auth_service.create_access_token(user.email)
        return Token(access_token=token)

    @router.post("/login", response_model=Token)
    def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)) -> Token:
        user = auth_service.authenticate_user(db, form_data.username, form_data.password)
        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciais inválidas")
        token = auth_service.create_access_token(user.email)
        return Token(access_token=token)

    @router.get("/me", response_model=UserProfile)
    def read_profile(current_user: User = Depends(get_current_user)) -> UserProfile:
        return UserProfile.model_validate(current_user)

    @router.put("/me", response_model=UserProfile)
    def update_profile(
        payload: UserUpdate,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user),
    ) -> UserProfile:
        updated = user_service.update_profile(db, current_user, payload)
        return UserProfile.model_validate(updated)

    @router.post("/templates", response_model=TemplateResponse, status_code=status.HTTP_201_CREATED)
    def create_template(
        payload: TemplateCreate,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user),
    ) -> TemplateResponse:
        template = user_service.create_template(db, current_user, payload)
        return TemplateResponse.model_validate(template)

    @router.get("/templates", response_model=List[TemplateResponse])
    def list_templates(
        db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
    ) -> List[TemplateResponse]:
        templates = user_service.list_templates(db, current_user)
        return [TemplateResponse.model_validate(t) for t in templates]

    @router.delete(
        "/templates/{template_id}",
        status_code=status.HTTP_204_NO_CONTENT,
        response_class=Response,
    )
    def delete_template(
        template_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user),
    ) -> Response:
        deleted = user_service.delete_template(db, current_user, template_id)
        if not deleted:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Modelo não encontrado")
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    return router
