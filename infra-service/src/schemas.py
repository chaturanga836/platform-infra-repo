from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


class ExistingInstance(BaseModel):
    instance_ref: str
    container_name: str
    host: str
    port: int = 5432
    admin_user: str
    admin_password: str


class CreateDatabaseRequest(BaseModel):
    workspace_id: int = Field(ge=1)
    engine: Literal["postgres", "mysql"] = "postgres"
    database_name: str = Field(min_length=1, max_length=63)
    existing_instance: Optional[ExistingInstance] = None


class ServiceInstanceInfo(BaseModel):
    instance_ref: str
    container_name: str
    host: str
    port: int
    admin_user: str
    admin_password: str
    created: bool


class DatabaseInfo(BaseModel):
    name: str
    engine: Literal["postgres", "mysql"]
    status: Literal["ready", "error"] = "ready"


class CreateDatabaseResponse(BaseModel):
    instance: ServiceInstanceInfo
    database: DatabaseInfo
    provisioned_at: datetime
