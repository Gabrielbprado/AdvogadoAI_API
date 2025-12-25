"""Pydantic schemas for auth, profile and templates."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    email: Optional[str] = None


class UserBase(BaseModel):
    email: EmailStr
    full_name: Optional[str] = None


class UserCreate(UserBase):
    # Bcrypt supports up to 72 bytes; keep a hard ceiling to avoid runtime errors.
    password: str = Field(min_length=8, max_length=72)


class UserProfile(UserBase):
    id: int
    instructions: Optional[str] = None
    avisos: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    instructions: Optional[str] = None
    avisos: Optional[str] = None


class TemplateBase(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    content: str = Field(min_length=4)


class TemplateCreate(TemplateBase):
    pass


class TemplateResponse(TemplateBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


class DocumentAnalysisRequest(BaseModel):
    template_id: Optional[int] = Field(default=None, description="ID de um modelo salvo do usuário")
    custom_request: Optional[str] = Field(default=None, description="Pedido específico para esta análise")
    instructions_override: Optional[str] = Field(default=None, description="Sobrescrever instruções do perfil")
    avisos_override: Optional[str] = Field(default=None, description="Sobrescrever avisos do perfil")
