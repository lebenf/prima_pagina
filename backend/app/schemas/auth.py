# Copyright (C) 2026 Lorenzo Benfeati
# SPDX-License-Identifier: AGPL-3.0-or-later
from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator


class LoginRequest(BaseModel):
    username: str  # accetta sia username che email
    password: str


class UserResponse(BaseModel):
    id: UUID
    email: str
    username: str
    preferred_lang: str
    role: str
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SessionResponse(BaseModel):
    id: UUID
    created_at: datetime
    expires_at: datetime
    last_active_at: datetime
    ip_address: str | None
    user_agent: str | None
    is_revoked: bool
    is_current: bool

    model_config = ConfigDict(from_attributes=True)


class UserCreate(BaseModel):
    email: EmailStr
    username: str = Field(min_length=3, max_length=100)
    password: str = Field(min_length=8)
    confirm_password: str = ""
    role: Literal["admin", "user"] = "user"
    preferred_lang: str = "it"

    @model_validator(mode="after")
    def passwords_match(self) -> "UserCreate":
        if self.confirm_password and self.password != self.confirm_password:
            raise ValueError("Le password non corrispondono")
        return self


class UserUpdate(BaseModel):
    preferred_lang: str | None = None
    current_password: str | None = None
    new_password: str | None = Field(default=None, min_length=8)
