from .db_session import SqlAlchemyBase
import sqlalchemy as sa
import datetime as dt
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from sqlalchemy_serializer import SerializerMixin


class User(SqlAlchemyBase, UserMixin, SerializerMixin):
    __tablename__ = 'Users'

    id = sa.Column(sa.Integer, primary_key=True, autoincrement=True, unique=True)
    username = sa.Column(sa.String, nullable=False)
    email = sa.Column(sa.String, nullable=False, unique=True, index=True)
    hashed_password = sa.Column(sa.String, nullable=False)
    crated_date = sa.Column(sa.DATETIME, default=dt.datetime.now())
    available_memory = sa.Column(sa.Float, default=5.0)
    is_account_pro = sa.Column(sa.Boolean, default=False)

    def __int__(self, *args, password, **kwargs):
        super.__init__(*args, **kwargs)
        self.set_password(password)

    def set_password(self, password):
        self.hashed_password = generate_password_hash(str(password))

    def check_password(self, password):
        return check_password_hash(self.hashed_password, str(password))
