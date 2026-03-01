from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime
from typing import Optional
import csv
import io
from app.db import get_db
from app.models import TradeLog
from app.schemas import TradeLogResponse

router = APIRouter(prefix="/api/sim/trades", tags=["trades"])

@router.get("", response_model=list[TradeLogResponse])
async def list_trades(
    user_id: int = Query(...),
    from_date: Optional[datetime] = Query(None, alias="from"),
    to_date: Optional[datetime] = Query(None, alias="to"),
    db: AsyncSession = Depends(get_db),
):
    q = select(TradeLog).where(TradeLog.user_id == user_id)
    if from_date:
        q = q.where(TradeLog.created_at >= from_date)
    if to_date:
        q = q.where(TradeLog.created_at <= to_date)
    q = q.order_by(TradeLog.created_at.desc())
    result = await db.execute(q)
    return result.scalars().all()

@router.get("/export")
async def export_trades(
    user_id: int = Query(...),
    db: AsyncSession = Depends(get_db),
):
    q = select(TradeLog).where(TradeLog.user_id == user_id).order_by(TradeLog.created_at.desc())
    result = await db.execute(q)
    logs = result.scalars().all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["id", "position_id", "leg_id", "action", "details", "created_at"])
    for log in logs:
        writer.writerow([log.id, log.position_id, log.leg_id, log.action, str(log.details), log.created_at])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=trades.csv"},
    )
