from datetime import datetime
import enum
from uuid import uuid4
from sqlalchemy.schema import Column
from sqlalchemy.types import UUID, Boolean, DateTime, Enum
from confs.main import db



class Roles(enum.Enum):
    SIMPLE = "simple"
    PARTICIPANT = "participant"
    ORGANISATEUR = "organisateur"
    ADMIN = "admin"

# Référez vous à la doc pour gérer ça
# https://flask-sqlalchemy.readthedocs.io/en/stable/quickstart/
# https://www.youtube.com/watch?v=uNmWxvvyBGU
# https://flask-sqlalchemy.readthedocs.io/en/stable/models/
class User(db.Model):
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    name = Column(db.String(20), nullable=False)
    password = Column(db.String(), nullable=False)
    username = Column(db.String(50), nullable=False)
    email = Column(db.String(255), nullable=False)
    is_active = Column(Boolean(), default=True)
    is_admin = Column(Boolean(), default=False)
    # role = Column(Enum(Roles), default=Roles.PARTICIPANT)
    created_at = Column(DateTime(), default=datetime.now())
    updated_at = Column(DateTime(), default=datetime.now())

    def __repr__(self) -> str:
        return f"<User: {self.name} | {self.username}>"

    
