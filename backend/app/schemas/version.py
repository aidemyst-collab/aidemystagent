from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime
from uuid import UUID


class VersionBase(BaseModel):
    """Base version schema."""
    version_tag: Optional[str] = None
    description: Optional[str] = None
    changelog: Optional[str] = None


class VersionCreate(VersionBase):
    """Schema for creating a version."""
    config: Dict[str, Any]


class VersionResponse(VersionBase):
    """Schema for version response."""
    id: UUID
    agent_id: UUID
    version_number: int
    config: Dict[str, Any]
    created_by: UUID
    created_at: datetime

    class Config:
        from_attributes = True


class VersionList(BaseModel):
    """Schema for version list response."""
    versions: list[VersionResponse]
    total: int


class VersionCompare(BaseModel):
    """Schema for comparing two versions."""
    version1: VersionResponse
    version2: VersionResponse
    differences: Dict[str, Any]
