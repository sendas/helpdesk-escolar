from pydantic import BaseModel, ConfigDict


class CategoryCreate(BaseModel):
    name: str
    description: str | None = None
    email_to: str | None = None
    color: str = "#1976D2"
    icon: str = "help_outline"
    sla_hours: int = 48
    warning_enabled: bool = False
    warning_text: str | None = None


class CategoryUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    email_to: str | None = None
    color: str | None = None
    icon: str | None = None
    sla_hours: int | None = None
    warning_enabled: bool | None = None
    warning_text: str | None = None


class CategoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None = None
    email_to: str | None = None
    color: str
    icon: str
    sla_hours: int
    warning_enabled: bool = False
    warning_text: str | None = None
