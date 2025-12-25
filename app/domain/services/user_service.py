"""User and template management services."""
from __future__ import annotations

from typing import List, Optional

from sqlalchemy.orm import Session

from app.domain.models.user_models import TemplateCreate, UserUpdate
from app.infrastructure.db.entities import PromptTemplate, User


class UserService:
    """Encapsulates profile updates and prompt template CRUD."""

    def get_user(self, session: Session, user_id: int) -> Optional[User]:
        return session.get(User, user_id)

    def get_user_by_email(self, session: Session, email: str) -> Optional[User]:
        return session.query(User).filter(User.email == email).first()

    def update_profile(self, session: Session, user: User, payload: UserUpdate) -> User:
        if payload.full_name is not None:
            user.full_name = payload.full_name
        if payload.instructions is not None:
            user.instructions = payload.instructions
        if payload.avisos is not None:
            user.avisos = payload.avisos
        session.add(user)
        session.commit()
        session.refresh(user)
        return user

    def create_template(self, session: Session, user: User, payload: TemplateCreate) -> PromptTemplate:
        template = PromptTemplate(name=payload.name, content=payload.content, owner=user)
        session.add(template)
        session.commit()
        session.refresh(template)
        return template

    def list_templates(self, session: Session, user: User) -> List[PromptTemplate]:
        return session.query(PromptTemplate).filter(PromptTemplate.owner_id == user.id).order_by(PromptTemplate.created_at.desc()).all()

    def get_template(self, session: Session, user: User, template_id: int) -> Optional[PromptTemplate]:
        return (
            session.query(PromptTemplate)
            .filter(PromptTemplate.id == template_id, PromptTemplate.owner_id == user.id)
            .first()
        )

    def delete_template(self, session: Session, user: User, template_id: int) -> bool:
        template = self.get_template(session, user, template_id)
        if not template:
            return False
        session.delete(template)
        session.commit()
        return True
