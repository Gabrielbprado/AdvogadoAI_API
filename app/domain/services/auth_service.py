"""Authentication and password/JWT helpers."""
from __future__ import annotations

import datetime as dt
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.config.settings import Settings
from app.infrastructure.db.entities import User


class AuthService:
    """Handles password hashing, verification and JWT token issuance."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        return self._pwd_context.verify(plain_password, hashed_password)

    def get_password_hash(self, password: str) -> str:
        if len(password.encode("utf-8")) > 72:
            # Bcrypt truncates silently after 72 bytes; reject to avoid user confusion.
            raise ValueError("Senha muito longa; use até 72 caracteres")
        return self._pwd_context.hash(password)

    def create_access_token(self, subject: str) -> str:
        expire_minutes = self._settings.access_token_expire_minutes
        expire = dt.datetime.utcnow() + dt.timedelta(minutes=expire_minutes)
        to_encode = {"sub": subject, "exp": expire}
        return jwt.encode(to_encode, self._settings.jwt_secret_key, algorithm=self._settings.jwt_algorithm)

    def decode_token_subject(self, token: str) -> Optional[str]:
        try:
            payload = jwt.decode(token, self._settings.jwt_secret_key, algorithms=[self._settings.jwt_algorithm])
            return payload.get("sub")
        except JWTError:
            return None

    def authenticate_user(self, session: Session, email: str, password: str) -> Optional[User]:
        user = session.query(User).filter(User.email == email).first()
        if not user:
            return None
        if not self.verify_password(password, user.hashed_password):
            return None
        return user

    def create_user(self, session: Session, *, email: str, password: str, full_name: str | None) -> User:
        hashed = self.get_password_hash(password)
        user = User(email=email, hashed_password=hashed, full_name=full_name)
        session.add(user)
        session.commit()
        session.refresh(user)
        return user
