from pydantic import BaseModel
from typing import Dict


class UserCreate(BaseModel):
    name: str


class UserUpdate(BaseModel):
    old_name: str
    new_name: str


class BalanceUpdate(BaseModel):
    name: str
    symbol: str
    amount: float


class UserBalancesResponse(BaseModel):
    balances: Dict[str, float]


class UserNetworth(BaseModel):
    name: str
    currency: str = "usd"
