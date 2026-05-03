from pydantic import BaseModel, ConfigDict


class SchoolCreate(BaseModel):
    name: str
    short_name: str
    address: str | None = None


class SchoolRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    short_name: str
    address: str | None = None
