from pydantic import BaseModel, EmailStr, UUID4, Field, ConfigDict
from datetime import datetime
from typing import Optional
from app.models.user import UserRole


class UserBase(BaseModel):
    email: EmailStr


class UserCreate(UserBase):
    password: str
    organization_id: str  # Required: user must select an organization
    role: Optional[UserRole] = None  # Optional: defaults to CREATOR if not provided


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(UserBase):
    id: UUID4
    role: UserRole
    organization_id: UUID4 = Field(..., serialization_alias="organizationId")
    created_at: datetime = Field(..., serialization_alias="createdAt")

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True
    )


class TokenPair(BaseModel):
    access_token: str = Field(..., serialization_alias="accessToken")
    refresh_token: str = Field(..., serialization_alias="refreshToken")
    token_type: str = Field(default="bearer", serialization_alias="tokenType")

    model_config = ConfigDict(
        populate_by_name=True
    )


class LoginResponse(BaseModel):
    user: UserResponse
    tokens: TokenPair


class RegisterResponse(BaseModel):
    user: UserResponse
    tokens: TokenPair


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class PasswordResetRequest(BaseModel):
    email: EmailStr
