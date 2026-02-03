import sqlalchemy as sa
import sqlalchemy.orm as so
from datetime import datetime
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
    signed_up_on: so.Mapped[datetime] = so.mapped_column(sa.DateTime, default=datetime.utcnow, nullable=False)



    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

@login.user_loader
def load_user(user_id: str) -> Optional["User"]:
    if not user_id:
        return None
    return db.session.get(User, int(user_id))