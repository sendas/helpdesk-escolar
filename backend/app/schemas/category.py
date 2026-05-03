from pydantic import BaseModel, ConfigDict


class CategoryCreate(BaseModel):
    name: str
    description: str | None = None
    color: str = "#1976D2"
    icon: str = "help_outline"
    sla_hours: int = 24


class CategoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None = None
    color: str
    icon: str
    sla_hours: int
