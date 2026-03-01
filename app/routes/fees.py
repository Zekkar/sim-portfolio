from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db import get_db
from app.models import ContractFee
from app.schemas import ContractFeeResponse, ContractFeeUpdate

router = APIRouter(prefix="/api/sim/fees", tags=["fees"])

@router.get("", response_model=list[ContractFeeResponse])
async def list_fees(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ContractFee).order_by(ContractFee.id))
    return result.scalars().all()

@router.put("/{contract_type}", response_model=ContractFeeResponse)
async def update_fee(contract_type: str, req: ContractFeeUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ContractFee).where(ContractFee.contract_type == contract_type))
    fee = result.scalar_one_or_none()
    if not fee:
        raise HTTPException(404, "合約類型不存在")
    for field, value in req.model_dump(exclude_none=True).items():
        setattr(fee, field, value)
    await db.commit()
    await db.refresh(fee)
    return fee
