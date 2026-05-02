import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select

# ─── 步驟 1：最先初始化 logging（讓後續所有 log 都結構化）────
from app.logging_config import setup_logging
setup_logging("sim-portfolio")

logger = logging.getLogger(__name__)

from app.db import engine, Base, async_session
from app.models import ContractFee
from app.routes.users import router as users_router
from app.routes.fees import router as fees_router
from app.routes.positions import router as positions_router
from app.routes.trades import router as trades_router
from app.telemetry_config import setup_telemetry, shutdown_telemetry
import app.models  # noqa: F401

SERVICE_NAME = "sim-portfolio"
SERVICE_NAMESPACE = "sim-portfolio"


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ─── 步驟 2：啟動時初始化 OTel（app 建立後才呼叫）────
    setup_telemetry(
        service_name=SERVICE_NAME,
        service_namespace=SERVICE_NAMESPACE,
        app=app,
        enable_asyncpg=True,
    )
    logger.info("sim-portfolio starting", extra={"port": 8897})

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # seed 預設費率
    async with async_session() as session:
        result = await session.execute(select(ContractFee))
        if not result.scalars().first():
            defaults = [
                ContractFee(contract_type="large_index", fee_per_lot=36, tax_rate=0.00002, multiplier=200),
                ContractFee(contract_type="mini_index", fee_per_lot=18, tax_rate=0.00002, multiplier=50),
                ContractFee(contract_type="micro_index", fee_per_lot=16, tax_rate=0.00002, multiplier=5),
                ContractFee(contract_type="stock_futures", fee_per_lot=16, tax_rate=0.00002, multiplier=2000),
                ContractFee(contract_type="etf_futures", fee_per_lot=16, tax_rate=0.00002, multiplier=10000),
            ]
            session.add_all(defaults)
            await session.commit()

    yield

    logger.info("sim-portfolio shutting down")
    shutdown_telemetry()
    await engine.dispose()


app = FastAPI(title="Sim Portfolio API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(users_router)
app.include_router(fees_router)
app.include_router(positions_router)
app.include_router(trades_router)


@app.get("/health")
async def health():
    """健康檢查端點（STANDARDS.md §3.4）— Dockerfile HEALTHCHECK 打此端點"""
    return {"status": "ok"}


@app.get("/api/sim/health")
async def health_legacy():
    """保留舊路徑向後相容"""
    return {"status": "ok"}
