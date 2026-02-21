from datetime import datetime
from uuid import uuid4
from sqlalchemy.types import UUID, DateTime, String, Float, JSON
from confs.main import db

class Submission(db.Model):
    __tablename__ = "submissions"
    
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    
    # Relations
    user_id = db.Column(UUID(as_uuid=True), db.ForeignKey("users.id"), nullable=False)
    competition_id = db.Column(UUID(as_uuid=True), db.ForeignKey("competitions.id"), nullable=False)
    
    # Fichier du modèle (h5, pkl, pt, onnx)
    model_path = db.Column(String(500), nullable=False)
    model_type = db.Column(String(10), nullable=False) # ex: 'onnx', 'h5'
    
    # Métriques (Stockage flexible)
    # On utilise Float pour le score principal et JSON pour le détail
    score = db.Column(Float, nullable=True) # Score de référence (ex: Accuracy)
    metrics_detail = db.Column(JSON, nullable=True) # ex: {"f1": 0.85, "precision": 0.82}
    
    status = db.Column(String(20), default="pending") # pending, processing, completed, failed
    
    created_at = db.Column(DateTime(), default=datetime.now)

    # Relations ORM
    user = db.relationship("User", backref="submissions")
    competition = db.relationship("Competition", backref="submissions")
