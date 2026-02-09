import sqlalchemy as sa
import sqlalchemy.orm as so
from datetime import datetime, timezone
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app import db, login
from typing import Optional

class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id: so.Mapped[int] = so.mapped_column(primary_key=True)
    email: so.Mapped[str] = so.mapped_column(sa.String(120), unique=True, index=True, nullable=False)
    name: so.Mapped[str] = so.mapped_column(sa.String(120), nullable=False)
    password_hash: so.Mapped[str] = so.mapped_column(sa.String(256), nullable=False)
    signed_up_on: so.Mapped[datetime] = so.mapped_column(sa.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationship
    customer: so.Mapped[Optional["Customer"]] = so.relationship(back_populates="user")



    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

@login.user_loader
def load_user(user_id: str) -> Optional["User"]:
    if not user_id:
        return None
    return db.session.get(User, int(user_id))

class Customer(db.Model):
    __tablename__ = 'customers'

    id: so.Mapped[int] = so.mapped_column(primary_key=True)
    user_id: so.Mapped[int] = so.mapped_column(sa.ForeignKey('users.id'), nullable=False)
    stripe_customer_id: so.Mapped[str] = so.mapped_column(sa.String(255), unique=True, nullable=False)
    created_at: so.Mapped[datetime] = so.mapped_column(sa.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    customer_name: so.Mapped[str] = so.mapped_column(sa.String(255), nullable=True)
    # Relationship
    user: so.Mapped["User"] = so.relationship(back_populates="customer")
    subscriptions: so.Mapped[list["Subscription"]] = so.relationship(back_populates="customer")


class Subscription(db.Model):
    __tablename__ = 'subscriptions'

    id: so.Mapped[int] = so.mapped_column(primary_key=True)
    stripe_customer_id: so.Mapped[str] = so.mapped_column(sa.ForeignKey('customers.stripe_customer_id'), nullable=False)
    stripe_subscription_id: so.Mapped[str] = so.mapped_column(sa.String(255), unique=True, nullable=False)
    status: so.Mapped[str] = so.mapped_column(sa.String(50), nullable=False)
    product_id: so.Mapped[str] = so.mapped_column(sa.String(255), nullable=False)
    price_id: so.Mapped[str] = so.mapped_column(sa.String(255), nullable=False)
    created_at: so.Mapped[datetime] = so.mapped_column(sa.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
   
    # Relationship
    customer: so.Mapped["Customer"] = so.relationship(back_populates="subscriptions")

