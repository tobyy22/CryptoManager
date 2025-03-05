from fastapi import FastAPI, HTTPException, Depends, Header
from sqlalchemy.orm import Session
from database import get_db, init_db
from models import User, Balance
from schemas import UserCreate, BalanceUpdate, UserUpdate
from coingecko import get_crypto_prices, is_coin_supported_in_coingecko
from redis_cache import (
    cache_get_networth_for_user_in_currency,
    cache_set_networth_for_user_in_currency,
    cache_clear_user_networth,
    is_symbol_in_cache,
    update_symbol_in_cache,
)
from contextlib import asynccontextmanager
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(lifespan=lifespan)


def verify_user(db: Session, name: str, api_key: str):
    if not api_key:
        raise HTTPException(status_code=401, detail="API key is required")

    if not name:
        raise HTTPException(status_code=400, detail="Username is required")

    user = db.query(User).filter(User.name == name, User.api_key == api_key).first()

    if not user:
        raise HTTPException(status_code=403, detail="Invalid username or API key")

    return user


def verify_symbol(symbol):
    if is_symbol_in_cache(symbol):
        logging.info("Symbol is present in cache..")
        return

    if is_coin_supported_in_coingecko(symbol):
        logging.info(f"Updating symbol {symbol} in cache.")
        update_symbol_in_cache(symbol)
    else:
        raise HTTPException(status_code=404, detail="Symbol not found.")


# Create a new user
@app.post("/users/")
def create_user(user_data: UserCreate, db: Session = Depends(get_db)):
    existing_user = db.query(User).filter(User.name == user_data.name).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="User already exists")

    new_user = User(name=user_data.name)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    logging.info("User created")
    return {"message": "User created", "api_key": new_user.api_key}


@app.put("/users/")
def update_user_name(
    data: UserUpdate,
    db: Session = Depends(get_db),
    api_key: str = Header(None),
):
    user = verify_user(db, data.old_name, api_key)

    # Update the user's name
    user.name = data.new_name
    db.commit()
    db.refresh(user)

    return {"message": "User name updated successfully", "new_name": user.name}


@app.delete("/users/{name}")
def delete_user(
    name: str,
    db: Session = Depends(get_db),
    api_key: str = Header(None),
):
    user = verify_user(db, name, api_key)

    db.delete(user)
    db.commit()

    return {"message": "User deleted successfully"}


@app.post("/balances/")
def update_balance(
    data: BalanceUpdate,
    db: Session = Depends(get_db),
    api_key: str = Header(None),  # API key required in headers
):
    user = verify_user(db, data.name, api_key)
    verify_symbol(data.symbol)

    balance_entry = (
        db.query(Balance)
        .filter(Balance.user_id == user.id, Balance.symbol == data.symbol.upper())
        .first()
    )

    if balance_entry:
        balance_entry.amount += data.amount
    else:
        balance_entry = Balance(
            user_id=user.id, symbol=data.symbol.upper(), amount=data.amount
        )
        db.add(balance_entry)

    db.commit()
    db.refresh(balance_entry)

    cache_clear_user_networth(user.name)

    return {
        "message": f"Updated {user.name}'s {data.symbol.upper()} balance",
        "balance": balance_entry.amount,
    }


@app.get("/users/{user_name}/networth")
def get_user_networth(
    user_name: str,
    currency: str,
    db: Session = Depends(get_db),
    api_key: str = Header(None),
):
    user = verify_user(db, user_name, api_key)

    cached_networth = cache_get_networth_for_user_in_currency(user_name, currency)

    if cached_networth:
        return cached_networth

    balances = (
        db.query(Balance.symbol, Balance.amount)
        .filter(Balance.user_id == user.id)
        .all()
    )

    if not balances:
        return {"net_worth": 0, "currency": currency, "details": {}}

    crypto_symbols = [symbol.lower() for symbol, _ in balances]

    try:
        prices = get_crypto_prices(crypto_symbols, currency)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    total_net_worth = 0
    details = {}

    for symbol, amount in balances:
        symbol_lower = symbol.lower()
        if symbol_lower in prices:
            price = prices[symbol_lower][currency]
            total_value = amount * price
            total_net_worth += total_value
            details[symbol] = {
                "amount": amount,
                "price_per_unit": price,
                "total_value": total_value,
            }

    response_data = {
        "net_worth": total_net_worth,
        "currency": currency,
        "details": details,
    }

    cache_set_networth_for_user_in_currency(user_name, currency, response_data)

    return response_data
