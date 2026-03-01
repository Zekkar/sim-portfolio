from sqlalchemy import Column, Integer, String, Numeric, DateTime, Text, ForeignKey, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from app.db import Base


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    nickname = Column(String(50), unique=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    positions = relationship("Position", back_populates="user")


class Position(Base):
    __tablename__ = "positions"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    long_symbol = Column(String(20), nullable=False)
    long_name = Column(String(50), nullable=False)
    short_symbol = Column(String(20), nullable=False)
    short_name = Column(String(50), nullable=False)
    contract_type = Column(String(30), nullable=False)
    direction = Column(String(10), nullable=False)  # 'forward' | 'reverse'
    status = Column(String(10), nullable=False, default="open")
    opened_at = Column(DateTime(timezone=True), server_default=func.now())
    closed_at = Column(DateTime(timezone=True), nullable=True)
    note = Column(Text, nullable=True)
    user = relationship("User", back_populates="positions")
    legs = relationship("PositionLeg", back_populates="position", order_by="PositionLeg.id")


class PositionLeg(Base):
    __tablename__ = "position_legs"
    id = Column(Integer, primary_key=True)
    position_id = Column(Integer, ForeignKey("positions.id"), nullable=False)
    long_lots = Column(Integer, nullable=False)
    short_lots = Column(Integer, nullable=False)
    long_entry_price = Column(Numeric(12, 2), nullable=False)
    short_entry_price = Column(Numeric(12, 2), nullable=False)
    long_exit_price = Column(Numeric(12, 2), nullable=True)
    short_exit_price = Column(Numeric(12, 2), nullable=True)
    status = Column(String(10), nullable=False, default="open")
    opened_at = Column(DateTime(timezone=True), server_default=func.now())
    closed_at = Column(DateTime(timezone=True), nullable=True)
    entry_margin = Column(Numeric(12, 2), nullable=False)
    long_fee = Column(Numeric(10, 2), nullable=False, default=0)
    short_fee = Column(Numeric(10, 2), nullable=False, default=0)
    long_tax = Column(Numeric(10, 2), nullable=False, default=0)
    short_tax = Column(Numeric(10, 2), nullable=False, default=0)
    realized_pnl = Column(Numeric(12, 2), nullable=True)
    position = relationship("Position", back_populates="legs")


class TradeLog(Base):
    __tablename__ = "trade_logs"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    position_id = Column(Integer, ForeignKey("positions.id"), nullable=False)
    leg_id = Column(Integer, ForeignKey("position_legs.id"), nullable=True)
    action = Column(String(20), nullable=False)
    details = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class ContractFee(Base):
    __tablename__ = "contract_fees"
    id = Column(Integer, primary_key=True)
    contract_type = Column(String(30), unique=True, nullable=False)
    fee_per_lot = Column(Numeric(10, 2), nullable=False)
    tax_rate = Column(Numeric(10, 8), nullable=False)
    tick_size = Column(Numeric(10, 4), nullable=True)
    tick_value = Column(Numeric(10, 2), nullable=True)
    multiplier = Column(Integer, nullable=False)
