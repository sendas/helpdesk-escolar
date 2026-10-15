from pydantic import BaseModel, ConfigDict


class SchoolCreate(BaseModel):
    name: str
    short_name: str
    address: str | None = None


class RoomRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    school_id: int
    code: str | None = None
    name: str
    kind: str
    label: str
    active: bool = True


class RoomWrite(BaseModel):
    school_id: int
    code: str | None = None
    name: str
    kind: str = "Sala de aula"
    active: bool = True


class SchoolRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    short_name: str
    address: str | None = None
