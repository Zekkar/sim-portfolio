from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db import get_db
from app.models import User
from app.schemas import UserCreate, UserResponse

router = APIRouter(prefix="/api/sim/users", tags=["users"])

@router.get("", response_model=list[UserResponse])
async def list_users(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).order_by(User.id))
    return result.scalars().all()

@router.post("", response_model=UserResponse, status_code=201)
async def create_user(req: UserCreate, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(select(User).where(User.nickname == req.nickname))
    if existing.scalar_one_or_none():
        raise HTTPException(400, "暱稱已存在")
    user = User(nickname=req.nickname)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user
