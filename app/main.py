from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from sqlalchemy import select
from app.db import engine, Base, async_session
from app.models import ContractFee
from app.routes.users import router as users_router
from app.routes.fees import router as fees_router
from app.routes.positions import router as positions_router
import app.models  # noqa: F401

@asynccontextmanager
async def lifespan(app: FastAPI):
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

@app.get("/api/sim/health")
async def health():
    return {"status": "ok"}
