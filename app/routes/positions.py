from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from datetime import datetime, timezone
from app.db import get_db
from app.models import Position, PositionLeg, TradeLog
from app.schemas import (
    PositionOpenRequest, PositionAddRequest, CloseLegRequest,
    CloseAllRequest, PositionResponse,
)

router = APIRouter(prefix="/api/sim/positions", tags=["positions"])

@router.get("", response_model=list[PositionResponse])
async def list_positions(
    user_id: int = Query(...),
    status: str = Query(None),
    db: AsyncSession = Depends(get_db),
):
    q = select(Position).options(selectinload(Position.legs)).where(Position.user_id == user_id)
    if status:
        q = q.where(Position.status == status)
    q = q.order_by(Position.opened_at.desc())
    result = await db.execute(q)
    return result.scalars().unique().all()

@router.post("/open", response_model=PositionResponse, status_code=201)
async def open_position(req: PositionOpenRequest, db: AsyncSession = Depends(get_db)):
    pos = Position(
        user_id=req.user_id,
        long_symbol=req.long_symbol,
        long_name=req.long_name,
        short_symbol=req.short_symbol,
        short_name=req.short_name,
        contract_type=req.contract_type,
        direction=req.direction,
        status="open",
    )
    db.add(pos)
    await db.flush()

    leg = PositionLeg(
        position_id=pos.id,
        long_lots=req.long_lots,
        short_lots=req.short_lots,
        long_entry_price=req.long_entry_price,
        short_entry_price=req.short_entry_price,
        entry_margin=req.entry_margin,
        long_fee=req.long_fee,
        short_fee=req.short_fee,
        long_tax=req.long_tax,
        short_tax=req.short_tax,
        status="open",
    )
    db.add(leg)
    await db.flush()

    log = TradeLog(
        user_id=req.user_id,
        position_id=pos.id,
        leg_id=leg.id,
        action="open",
        details=req.model_dump(mode="json"),
    )
    db.add(log)
    await db.commit()

    result = await db.execute(
        select(Position).options(selectinload(Position.legs)).where(Position.id == pos.id)
    )
    return result.scalar_one()

@router.post("/{position_id}/add", response_model=PositionResponse)
async def add_leg(position_id: int, req: PositionAddRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Position).options(selectinload(Position.legs)).where(Position.id == position_id)
    )
    pos = result.scalar_one_or_none()
    if not pos or pos.status != "open":
        raise HTTPException(404, "倉位不存在或已平倉")

    leg = PositionLeg(
        position_id=position_id,
        long_lots=req.long_lots,
        short_lots=req.short_lots,
        long_entry_price=req.long_entry_price,
        short_entry_price=req.short_entry_price,
        entry_margin=req.entry_margin,
        long_fee=req.long_fee,
        short_fee=req.short_fee,
        long_tax=req.long_tax,
        short_tax=req.short_tax,
        status="open",
    )
    db.add(leg)
    await db.flush()

    log = TradeLog(
        user_id=pos.user_id,
        position_id=position_id,
        leg_id=leg.id,
        action="open",
        details=req.model_dump(mode="json"),
    )
    db.add(log)
    await db.commit()

    result = await db.execute(
        select(Position).options(selectinload(Position.legs)).where(Position.id == position_id)
    )
    return result.scalar_one()

@router.post("/{position_id}/close-leg/{leg_id}", response_model=PositionResponse)
async def close_leg(position_id: int, leg_id: int, req: CloseLegRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Position).options(selectinload(Position.legs)).where(Position.id == position_id)
    )
    pos = result.scalar_one_or_none()
    if not pos or pos.status != "open":
        raise HTTPException(404, "倉位不存在或已平倉")

    leg = next((l for l in pos.legs if l.id == leg_id and l.status == "open"), None)
    if not leg:
        raise HTTPException(404, "Leg 不存在或已平倉")

    now = datetime.now(timezone.utc)
    leg.long_exit_price = req.long_exit_price
    leg.short_exit_price = req.short_exit_price
    leg.long_fee = req.long_fee
    leg.short_fee = req.short_fee
    leg.long_tax = req.long_tax
    leg.short_tax = req.short_tax
    leg.realized_pnl = req.realized_pnl
    leg.status = "closed"
    leg.closed_at = now

    open_legs = [l for l in pos.legs if l.status == "open" and l.id != leg_id]
    if not open_legs:
        pos.status = "closed"
        pos.closed_at = now

    log = TradeLog(
        user_id=pos.user_id,
        position_id=position_id,
        leg_id=leg_id,
        action="close",
        details=req.model_dump(mode="json"),
    )
    db.add(log)
    await db.commit()

    result = await db.execute(
        select(Position).options(selectinload(Position.legs)).where(Position.id == position_id)
    )
    return result.scalar_one()

@router.post("/{position_id}/close-all", response_model=PositionResponse)
async def close_all_legs(position_id: int, req: CloseAllRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Position).options(selectinload(Position.legs)).where(Position.id == position_id)
    )
    pos = result.scalar_one_or_none()
    if not pos or pos.status != "open":
        raise HTTPException(404, "倉位不存在或已平倉")

    now = datetime.now(timezone.utc)
    leg_map = {l.id: l for l in pos.legs if l.status == "open"}

    for leg_data in req.legs:
        leg = leg_map.get(leg_data.leg_id)
        if not leg:
            continue
        leg.long_exit_price = leg_data.long_exit_price
        leg.short_exit_price = leg_data.short_exit_price
        leg.long_fee = leg_data.long_fee
        leg.short_fee = leg_data.short_fee
        leg.long_tax = leg_data.long_tax
        leg.short_tax = leg_data.short_tax
        leg.realized_pnl = leg_data.realized_pnl
        leg.status = "closed"
        leg.closed_at = now

    # 檢查是否所有 open legs 都已被關閉
    remaining_open = [l for l in pos.legs if l.status == "open"]
    if not remaining_open:
        pos.status = "closed"
        pos.closed_at = now

    log = TradeLog(
        user_id=pos.user_id,
        position_id=position_id,
        leg_id=None,
        action="close_all",
        details={"legs": [d.model_dump(mode="json") for d in req.legs]},
    )
    db.add(log)
    await db.commit()

    result = await db.execute(
        select(Position).options(selectinload(Position.legs)).where(Position.id == position_id)
    )
    return result.scalar_one()
