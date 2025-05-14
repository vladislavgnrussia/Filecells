from .db_session import SqlAlchemyBase
import sqlalchemy as sa
import datetime as dt
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from sqlalchemy_serializer import SerializerMixin


class Codes(SqlAlchemyBase, UserMixin, SerializerMixin):
    __tablename__ = 'Codes'

    id = sa.Column(sa.Integer, primary_key=True, autoincrement=True, unique=True)
    code = sa.Column(sa.String, unique=True, nullable=False)
    remain_using = sa.Column(sa.Integer, default=1)
