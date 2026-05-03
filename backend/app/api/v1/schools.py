from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_db, get_current_user, require_admin
from app.models.school import School
from app.models.user import User
from app.schemas.school import SchoolCreate, SchoolRead

router = APIRouter(prefix="/schools", tags=["schools"])


@router.get("", response_model=list[SchoolRead])
async def list_schools(db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    result = await db.execute(select(School).order_by(School.name))
    return result.scalars().all()


@router.post("", response_model=SchoolRead, status_code=status.HTTP_201_CREATED)
async def create_school(data: SchoolCreate, db: AsyncSession = Depends(get_db), _: User = Depends(require_admin)):
    school = School(**data.model_dump())
    db.add(school)
    await db.commit()
    await db.refresh(school)
    return school


@router.put("/{school_id}", response_model=SchoolRead)
async def update_school(school_id: int, data: SchoolCreate, db: AsyncSession = Depends(get_db), _: User = Depends(require_admin)):
    result = await db.execute(select(School).where(School.id == school_id))
    school = result.scalar_one_or_none()
    if not school:
        raise HTTPException(status_code=404, detail="School not found")
    for k, v in data.model_dump().items():
        setattr(school, k, v)
    await db.commit()
    await db.refresh(school)
    return school


@router.delete("/{school_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_school(school_id: int, db: AsyncSession = Depends(get_db), _: User = Depends(require_admin)):
    result = await db.execute(select(School).where(School.id == school_id))
    school = result.scalar_one_or_none()
    if not school:
        raise HTTPException(status_code=404, detail="School not found")
    await db.delete(school)
    await db.commit()
