from datetime import datetime
from uuid import uuid4
from sqlalchemy.types import UUID, DateTime, String, Float, JSON
from confs.main import db


class Submission(db.Model):
    """Représente la soumission d'un modèle IA par un participant à une compétition."""
    __tablename__ = "submissions"

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid4)

    # ── Relations ─────────────────────────────────────────────────────────────
    user_id        = db.Column(UUID(as_uuid=True), db.ForeignKey("users.id"),        nullable=False)
    competition_id = db.Column(UUID(as_uuid=True), db.ForeignKey("competitions.id"), nullable=False)

    # ── Fichier du modèle ─────────────────────────────────────────────────────
    # Formats supportés : h5, pkl, pt, onnx, joblib
    model_path = db.Column(String(500), nullable=False)
    model_type = db.Column(String(15),  nullable=False)  # 'sklearn', 'tensorflow', 'onnx', 'pytorch'

    # ── Métriques (stockage flexible) ─────────────────────────────────────────
    score          = db.Column(Float, nullable=True)  # Score principal (ex: accuracy)
    metrics_detail = db.Column(JSON,  nullable=True)  # {"f1": 0.85, "precision": 0.82}

    # ── Statut du traitement ──────────────────────────────────────────────────
    # Valeurs possibles : pending | processing | completed | failed
    status = db.Column(String(20), default="pending", nullable=False)

    # ── Horodatage ────────────────────────────────────────────────────────────
    created_at = db.Column(DateTime(), default=datetime.utcnow, nullable=False)

    # ── Relations ORM ─────────────────────────────────────────────────────────
    user        = db.relationship("User",        backref="submissions")
    competition = db.relationship("Competition", back_populates="submissions")

    def to_dict(self):
        """Sérialise la soumission pour la réponse API."""
        return {
            "id":             str(self.id),
            "user_id":        str(self.user_id),
            "competition_id": str(self.competition_id),
            "model_type":     self.model_type,
            "status":         self.status,
            "score":          self.score,
            "metrics_detail": self.metrics_detail,
            "created_at":     self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f"<Submission [{self.status}] user={self.user_id} comp={self.competition_id}>"
