from datetime import datetime
from enum import Enum as PyEnum
from confs.main import db
from sqlalchemy import Column, ForeignKey
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import relationship
from sqlalchemy.types import UUID, DateTime, String, Integer, Enum
from uuid import uuid4


# ─────────────────────────────────────────────
#  TABLE D'ASSOCIATION : participations
# ─────────────────────────────────────────────

participations = db.Table(
    'participations_competitions',
    db.Column("user_id",        db.UUID(as_uuid=True), db.ForeignKey("users.id"),        primary_key=True),
    db.Column("competition_id", db.UUID(as_uuid=True), db.ForeignKey("competitions.id"), primary_key=True),
    db.Column("team_name",      String(100),            nullable=True),
    db.Column("created_at",     DateTime(),             default=datetime.utcnow),
    db.Column("updated_at",     DateTime(),             default=datetime.utcnow),
)


# ─────────────────────────────────────────────
#  TABLE D'ASSOCIATION : organisateurs
# ─────────────────────────────────────────────

competition_organizers = db.Table(
    'competition_organizers',
    db.Column('competition_id', db.UUID(as_uuid=True), db.ForeignKey('competitions.id', ondelete='CASCADE'), primary_key=True),
    db.Column('user_id',        db.UUID(as_uuid=True), db.ForeignKey('users.id',        ondelete='CASCADE'), primary_key=True),
    db.Column('added_at',       db.DateTime, default=datetime.utcnow),
)


# ─────────────────────────────────────────────
#  ENUMS
# ─────────────────────────────────────────────

class CompetitionStatus(PyEnum):
    DRAFT     = "draft"       # En cours de création (non visible)
    UPCOMING  = "upcoming"    # À venir (visible, inscription possible)
    ACTIVE    = "active"      # En cours (soumissions ouvertes)
    CLOSED    = "closed"      # Soumissions fermées, résultats en calcul
    FINISHED  = "finished"    # Terminée (résultats publiés)
    ARCHIVED  = "archived"    # Archivée (lecture seule)


class TaskType(PyEnum):
    CLASSIFICATION  = "classification"
    REGRESSION      = "regression"
    CLUSTERING      = "clustering"
    NLP             = "nlp"
    COMPUTER_VISION = "computer_vision"


class MetricName(PyEnum):
    # Classification
    ACCURACY  = "accuracy"
    F1_SCORE  = "f1_score"
    PRECISION = "precision"
    RECALL    = "recall"
    AUC_ROC   = "auc_roc"
    LOG_LOSS  = "log_loss"
    # Régression
    RMSE = "rmse"
    MAE  = "mae"
    R2   = "r2"
    MAPE = "mape"


# Bibliothèque prédéfinie des métriques disponibles
METRICS_LIBRARY = {
    MetricName.ACCURACY:  {"label": "Accuracy",  "higher_is_better": True,  "task": "classification"},
    MetricName.F1_SCORE:  {"label": "F1-Score",  "higher_is_better": True,  "task": "classification"},
    MetricName.PRECISION: {"label": "Precision", "higher_is_better": True,  "task": "classification"},
    MetricName.RECALL:    {"label": "Recall",     "higher_is_better": True,  "task": "classification"},
    MetricName.AUC_ROC:   {"label": "AUC-ROC",   "higher_is_better": True,  "task": "classification"},
    MetricName.LOG_LOSS:  {"label": "Log Loss",   "higher_is_better": False, "task": "classification"},
    MetricName.RMSE:      {"label": "RMSE",       "higher_is_better": False, "task": "regression"},
    MetricName.MAE:       {"label": "MAE",        "higher_is_better": False, "task": "regression"},
    MetricName.R2:        {"label": "R² Score",   "higher_is_better": True,  "task": "regression"},
    MetricName.MAPE:      {"label": "MAPE",       "higher_is_better": False, "task": "regression"},
}


# ─────────────────────────────────────────────
#  MODÈLE PRINCIPAL : Competition
# ─────────────────────────────────────────────

class Competition(db.Model):
    __tablename__ = 'competitions'

    # ── Identifiant UUID (cohérent avec User et Submission) ──
    id     = db.Column(db.UUID(as_uuid=True), primary_key=True, default=uuid4)
    slug   = db.Column(db.String(120), unique=True, nullable=False, index=True)  # URL-friendly
    title  = db.Column(db.String(255), nullable=False)
    status = db.Column(db.Enum(CompetitionStatus, native_enum=False), nullable=False, default=CompetitionStatus.DRAFT, index=True)
    task_type  = db.Column(db.Enum(TaskType, native_enum=False), nullable=False)
    created_by = db.Column(db.UUID(as_uuid=True), db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # ── Page de présentation ──────────────────
    description            = db.Column(db.Text, nullable=False)
    problem_statement      = db.Column(db.Text, nullable=True)   # Markdown — objectifs détaillés
    rules                  = db.Column(db.Text, nullable=True)   # Markdown — règlement
    data_description       = db.Column(db.Text, nullable=True)   # Markdown — description des données
    evaluation_description = db.Column(db.Text, nullable=True)   # Markdown — critères d'évaluation
    prizes     = db.Column(JSON, nullable=True)  # [{rank: 1, reward: "500€", label: "1er prix"}]
    faq        = db.Column(JSON, nullable=True)  # [{question: "...", answer: "..."}]
    banner_url = db.Column(db.String(512), nullable=True)

    # ── Calendrier ───────────────────────────
    registration_start = db.Column(db.DateTime, nullable=True)   # Ouverture inscriptions
    start_date         = db.Column(db.DateTime, nullable=False)   # Ouverture soumissions
    end_date           = db.Column(db.DateTime, nullable=False)   # Clôture soumissions
    results_date       = db.Column(db.DateTime, nullable=True)    # Publication résultats

    # ── Configuration métriques ───────────────
    primary_metric    = db.Column(db.Enum(MetricName, native_enum=False), nullable=False)
    secondary_metrics = db.Column(JSON, nullable=True)   # ["f1_score", "auc_roc"]
    evaluation_config = db.Column(JSON, nullable=True)   # Config avancée

    # ── Quotas et limites ─────────────────────
    max_submissions_per_day   = db.Column(db.Integer, nullable=False, default=10)
    max_submissions_total     = db.Column(db.Integer, nullable=False, default=50)
    max_file_size_mb          = db.Column(db.Integer, nullable=False, default=500)
    execution_timeout_seconds = db.Column(db.Integer, nullable=False, default=120)
    allowed_formats           = db.Column(JSON, nullable=False,
                                          default=lambda: [".pkl", ".h5", ".pt", ".onnx", ".joblib"])

    # ── Datasets ──────────────────────────────
    train_dataset_url     = db.Column(db.String(512), nullable=True)  # URL téléchargement public
    train_dataset_path    = db.Column(db.String(512), nullable=True)  # Chemin serveur
    test_dataset_path     = db.Column(db.String(512), nullable=True)  # JAMAIS exposé publiquement
    sample_submission_url = db.Column(db.String(512), nullable=True)

    # ── Relations ─────────────────────────────
    organizers   = db.relationship('User', secondary=competition_organizers,
                                   backref='organized_competitions', lazy='select')
    creator      = db.relationship('User', foreign_keys=[created_by],
                                   back_populates='created_competitions')
    participants = db.relationship('User', secondary=participations,
                                   back_populates='participations_list')
    submissions  = db.relationship('Submission', back_populates='competition',
                                   lazy='dynamic', cascade='all, delete-orphan')

    # ─────────────────────────────────────────
    #  PROPRIÉTÉS CALCULÉES
    # ─────────────────────────────────────────

    @property
    def is_accepting_submissions(self):
        """Retourne True si la compétition accepte actuellement des soumissions."""
        now = datetime.utcnow()
        return (
            self.status == CompetitionStatus.ACTIVE
            and self.start_date <= now <= self.end_date
        )

    @property
    def days_remaining(self):
        """Nombre de jours restants avant la clôture des soumissions."""
        if self.status != CompetitionStatus.ACTIVE:
            return None
        delta = self.end_date - datetime.utcnow()
        return max(0, delta.days)

    @property
    def primary_metric_info(self):
        """Retourne les métadonnées de la métrique principale."""
        return METRICS_LIBRARY.get(self.primary_metric, {})

    @property
    def total_submissions(self):
        """Nombre total de soumissions pour cette compétition."""
        return self.submissions.count()

    @property
    def participants_count(self):
        """Nombre de participants distincts."""
        from models.submission import Submission
        return db.session.query(
            db.func.count(db.distinct(Submission.user_id))
        ).filter(Submission.competition_id == self.id).scalar() or 0

    # ─────────────────────────────────────────
    #  MÉTHODES MÉTIER
    # ─────────────────────────────────────────

    def can_user_submit(self, user):
        """Vérifie si un utilisateur peut soumettre (quota + statut).

        Returns:
            tuple: (bool, str) — (autorisé, message explicatif)
        """
        if not self.is_accepting_submissions:
            return False, "La compétition n'accepte pas de soumissions actuellement."

        from models.submission import Submission
        from sqlalchemy import func, cast, Date

        today = datetime.utcnow().date()

        # Quota journalier
        daily_count = Submission.query.filter(
            Submission.competition_id == self.id,
            Submission.user_id == user.id,
            cast(Submission.created_at, Date) == today,
        ).count()

        if daily_count >= self.max_submissions_per_day:
            return False, f"Quota journalier atteint ({self.max_submissions_per_day}/jour)."

        # Quota total
        total_count = Submission.query.filter_by(
            competition_id=self.id,
            user_id=user.id,
        ).count()

        if total_count >= self.max_submissions_total:
            return False, f"Quota total atteint ({self.max_submissions_total} soumissions max)."

        return True, "OK"

    def auto_update_status(self):
        """Met à jour le statut automatiquement selon les dates."""
        now = datetime.utcnow()

        if self.status in (CompetitionStatus.DRAFT, CompetitionStatus.ARCHIVED):
            return  # Ces statuts sont gérés manuellement

        if now < self.start_date:
            self.status = CompetitionStatus.UPCOMING
        elif self.start_date <= now <= self.end_date:
            self.status = CompetitionStatus.ACTIVE
        elif now > self.end_date:
            if self.results_date and now >= self.results_date:
                self.status = CompetitionStatus.FINISHED
            else:
                self.status = CompetitionStatus.CLOSED

    def to_public_dict(self):
        """Sérialisation publique — NE contient jamais les chemins des données de test."""
        return {
            "id":                   str(self.id),
            "slug":                 self.slug,
            "title":                self.title,
            "status":               self.status.value,
            "task_type":            self.task_type.value,
            "description":          self.description,
            "problem_statement":    self.problem_statement,
            "rules":                self.rules,
            "data_description":     self.data_description,
            "evaluation_description": self.evaluation_description,
            "prizes":               self.prizes or [],
            "faq":                  self.faq or [],
            "banner_url":           self.banner_url,
            "calendar": {
                "registration_start": self._fmt(self.registration_start),
                "start_date":         self._fmt(self.start_date),
                "end_date":           self._fmt(self.end_date),
                "results_date":       self._fmt(self.results_date),
                "days_remaining":     self.days_remaining,
            },
            "metrics": {
                "primary":   self.primary_metric.value,
                "secondary": self.secondary_metrics or [],
                "info":      self.primary_metric_info,
            },
            "config": {
                "max_submissions_per_day":   self.max_submissions_per_day,
                "max_submissions_total":     self.max_submissions_total,
                "max_file_size_mb":          self.max_file_size_mb,
                "execution_timeout_seconds": self.execution_timeout_seconds,
                "allowed_formats":           self.allowed_formats,
            },
            "downloads": {
                "train_dataset":     self.train_dataset_url,
                "sample_submission": self.sample_submission_url,
                # ⚠️  test_dataset_path est volontairement absent
            },
            "stats": {
                "total_submissions": self.total_submissions,
                "participants":      self.participants_count,
            },
            "created_at": self._fmt(self.created_at),
        }

    def to_admin_dict(self):
        """Sérialisation complète pour admin/organisateur."""
        data = self.to_public_dict()
        data["admin"] = {
            "test_dataset_path":  self.test_dataset_path,
            "train_dataset_path": self.train_dataset_path,
            "created_by":         str(self.created_by) if self.created_by else None,
            "organizers":         [str(u.id) for u in self.organizers],
            "evaluation_config":  self.evaluation_config,
        }
        return data

    @staticmethod
    def _fmt(dt):
        """Formate un datetime en ISO 8601, ou None si absent."""
        return dt.isoformat() if dt else None

    def __repr__(self):
        return f"<Competition [{self.status.value}] {self.title!r}>"


# ─────────────────────────────────────────────
#  MODÈLE : Annonces de compétition
# ─────────────────────────────────────────────

class CompetitionAnnouncement(db.Model):
    """Annonces publiées pendant une compétition (mises à jour importantes)."""
    __tablename__ = 'competition_announcements'

    id             = db.Column(db.UUID(as_uuid=True), primary_key=True, default=uuid4)
    competition_id = db.Column(db.UUID(as_uuid=True), db.ForeignKey('competitions.id', ondelete='CASCADE'), nullable=False)
    title          = db.Column(db.String(255), nullable=False)
    content        = db.Column(db.Text, nullable=False)   # Markdown
    is_pinned      = db.Column(db.Boolean, default=False)
    created_by     = db.Column(db.UUID(as_uuid=True), db.ForeignKey('users.id'))
    created_at     = db.Column(db.DateTime, default=datetime.utcnow)

    competition = db.relationship('Competition', backref=db.backref('announcements', lazy='dynamic'))
    author      = db.relationship('User', foreign_keys=[created_by])

    def to_dict(self):
        return {
            "id":         str(self.id),
            "title":      self.title,
            "content":    self.content,
            "is_pinned":  self.is_pinned,
            "author":     self.author.username if self.author else None,
            "created_at": self._fmt(self.created_at),
        }

    @staticmethod
    def _fmt(dt):
        return dt.isoformat() if dt else None
