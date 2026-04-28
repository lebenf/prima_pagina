# Copyright (C) 2026 Lorenzo Benfeati
# SPDX-License-Identifier: AGPL-3.0-or-later
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator


class InvitationCreate(BaseModel):
    email: EmailStr | None = None
    expires_days: int = Field(default=7, ge=1, le=30)


class InvitationResponse(BaseModel):
    id: UUID
    token: UUID
    email: str | None
    created_at: datetime
    expires_at: datetime
    used_at: datetime | None
    is_valid: bool
    invite_url: str

    model_config = ConfigDict(from_attributes=True)


class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=100)
    email: EmailStr
    password: str = Field(min_length=8)
    confirm_password: str

    @model_validator(mode="after")
    def passwords_match(self) -> "RegisterRequest":
        if self.password != self.confirm_password:
            raise ValueError("Le password non corrispondono")
        return self


class InvitationValidateResponse(BaseModel):
    valid: bool
    email: str | None
    expires_at: datetime | None
