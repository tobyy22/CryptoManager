import uuid
import secrets
from sqlalchemy import Column, String, Float, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        unique=True,
        nullable=False,
    )
    name = Column(String(100), unique=True, nullable=False, index=True)
    api_key = Column(
        String(64), unique=True, nullable=False, default=lambda: secrets.token_hex(32)
    )
    balances = relationship(
        "Balance",
        back_populates="user",
        cascade="all, delete",
    )


class Balance(Base):
    __tablename__ = "balances"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        unique=True,
        nullable=False,
    )
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),  # Ensures DB-level cascading delete
        nullable=False,
    )
    symbol = Column(String(10), nullable=False)
    amount = Column(Float, nullable=False, default=0.0)

    user = relationship("User", back_populates="balances")

    __table_args__ = (UniqueConstraint("user_id", "symbol", name="unique_user_crypto"),)
