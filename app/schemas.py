from pydantic import BaseModel
from datetime import datetime
from typing import Optional
from decimal import Decimal


# --- Users ---
class UserCreate(BaseModel):
    nickname: str


class UserResponse(BaseModel):
    id: int
    nickname: str
    created_at: datetime


# --- Contract Fees ---
class ContractFeeResponse(BaseModel):
    contract_type: str
    fee_per_lot: Decimal
    tax_rate: Decimal
    tick_size: Optional[Decimal] = None
    tick_value: Optional[Decimal] = None
    multiplier: int


class ContractFeeUpdate(BaseModel):
    fee_per_lot: Optional[Decimal] = None
    tax_rate: Optional[Decimal] = None
    tick_size: Optional[Decimal] = None
    tick_value: Optional[Decimal] = None
    multiplier: Optional[int] = None


# --- Position Legs ---
class LegResponse(BaseModel):
    id: int
    long_lots: int
    short_lots: int
    long_entry_price: Decimal
    short_entry_price: Decimal
    long_exit_price: Optional[Decimal] = None
    short_exit_price: Optional[Decimal] = None
    status: str
    opened_at: datetime
    closed_at: Optional[datetime] = None
    entry_margin: Decimal
    long_fee: Decimal
    short_fee: Decimal
    long_tax: Decimal
    short_tax: Decimal
    realized_pnl: Optional[Decimal] = None


# --- Close Leg Data (must be before CloseAllRequest) ---
class CloseLegData(BaseModel):
    leg_id: int
    long_exit_price: Decimal
    short_exit_price: Decimal
    long_fee: Decimal
    short_fee: Decimal
    long_tax: Decimal
    short_tax: Decimal
    realized_pnl: Decimal


# --- Positions ---
class PositionOpenRequest(BaseModel):
    user_id: int
    long_symbol: str
    long_name: str
    short_symbol: str
    short_name: str
    contract_type: str
    direction: str
    long_lots: int
    short_lots: int
    long_entry_price: Decimal
    short_entry_price: Decimal
    entry_margin: Decimal
    long_fee: Decimal
    short_fee: Decimal
    long_tax: Decimal
    short_tax: Decimal


class PositionAddRequest(BaseModel):
    long_lots: int
    short_lots: int
    long_entry_price: Decimal
    short_entry_price: Decimal
    entry_margin: Decimal
    long_fee: Decimal
    short_fee: Decimal
    long_tax: Decimal
    short_tax: Decimal


class CloseLegRequest(BaseModel):
    long_exit_price: Decimal
    short_exit_price: Decimal
    long_fee: Decimal
    short_fee: Decimal
    long_tax: Decimal
    short_tax: Decimal
    realized_pnl: Decimal


class CloseAllRequest(BaseModel):
    legs: list[CloseLegData]


class PositionResponse(BaseModel):
    id: int
    user_id: int
    long_symbol: str
    long_name: str
    short_symbol: str
    short_name: str
    contract_type: str
    direction: str
    status: str
    opened_at: datetime
    closed_at: Optional[datetime] = None
    note: Optional[str] = None
    legs: list[LegResponse] = []


# --- Trade Logs ---
class TradeLogResponse(BaseModel):
    id: int
    user_id: int
    position_id: int
    leg_id: Optional[int] = None
    action: str
    details: Optional[dict] = None
    created_at: datetime
