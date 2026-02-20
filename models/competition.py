
from datetime import datetime
from sqlalchemy import Column, ForeignKey
from sqlalchemy.orm import relationship
from confs.main import db
from sqlalchemy.types import UUID, DateTime, String
from uuid import uuid4


participations = db.Table(
        'participations_competitions', 
        db.Column("user_id", db.UUID(as_uuid=True), db.ForeignKey("users.id"), primary_key=True),
        db.Column("competition_id", db.UUID(as_uuid=True), db.ForeignKey("competitions.id"), primary_key=True),
        db.Column("team_name", String(100), nullable=True),
        db.Column("created_at", DateTime(), default=datetime.now),
        db.Column("updated_at", DateTime(), default=datetime.now)
)

class Competition(db.Model):
    __tablename__ = "competitions"
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    name = Column(db.String(255), nullable=False, comment="Le nom de la compétition")
    description = Column(String(1000), nullable=True)
    created_by = Column(UUID(), ForeignKey('users.id'))

    created_at = db.Column(DateTime(), default=datetime.now())
    updated_at = db.Column(DateTime(), default=datetime.now())

    participants = relationship('User', secondary=participations, back_populates='participations_list')

    creator = relationship("User", back_populates="created_competitions")
    
    raw_dataset_path = Column(String(500), nullable=False)    # Dataset brut
    processed_dataset_path = Column(String(500), nullable=False) # Dataset traité 
    evaluation_metric = Column(String(50), default="accuracy")

