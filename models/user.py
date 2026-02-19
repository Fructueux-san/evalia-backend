from sqlalchemy.schema import Column
from sqlalchemy.types import Boolean
from confs.main import db


# Référez vous à la doc pour gérer ça
# https://flask-sqlalchemy.readthedocs.io/en/stable/quickstart/
# https://www.youtube.com/watch?v=uNmWxvvyBGU
# https://flask-sqlalchemy.readthedocs.io/en/stable/models/
class User(db.Model):
    id = Column(db.Integer, primary_key=True)
    name = Column(db.String(20), nullable=False)
    password = Column(db.String, nullable=False)
    username = Column(db.String(50), nullable=False)
    email = Column(db.String(255), nullable=False)
    is_active = Column(Boolean(), default=True)

    def __repr__(self) -> str:
        return f"<User: {self.name} | {self.username}>"

    
