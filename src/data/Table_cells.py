from .db_session import SqlAlchemyBase
import sqlalchemy as sa
import datetime as dt
from werkzeug.security import generate_password_hash, check_password_hash


class Cell(SqlAlchemyBase):
    __tablename__ = 'Cells'

    id = sa.Column(sa.Integer, primary_key=True, autoincrement=True, unique=True)
    user_id = sa.Column(sa.Integer, sa.ForeignKey('Users.id'))
    cellname = sa.Column(sa.String, nullable=False)
    is_private = sa.Column(sa.Boolean, default=False)
    hashed_password = sa.Column(sa.String, nullable=True)
    path = sa.Column(sa.String, nullable=False, unique=True)
    created_date = sa.Column(sa.DATETIME, default=dt.datetime.now())
    weight_of_directory = sa.Column(sa.Float, nullable=False)

    def __init__(self, *args, password, **kwargs):
        super().__init__(*args, **kwargs)
        self.set_password(password)

    def set_password(self, password):
        self.hashed_password = generate_password_hash(str(password))

    def check_password(self, password):
        return check_password_hash(self.hashed_password, str(password))
