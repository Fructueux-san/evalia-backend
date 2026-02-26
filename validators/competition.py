"""
Schémas de validation Marshmallow pour les compétitions.
"""

from marshmallow import Schema, fields, validate, validates_schema, ValidationError
from datetime import datetime


class CreateCompetitionSchema(Schema):
    """Valide les données de création d'une compétition."""

    # Champs requis
    slug  = fields.Str(required=True, validate=validate.Regexp(
        r'^[a-z0-9]+(?:-[a-z0-9]+)*$',
        error="Le slug doit être en minuscules avec des tirets (ex: ma-competition-2024)"
    ))
    title       = fields.Str(required=True, validate=validate.Length(min=3, max=255))
    description = fields.Str(required=True, validate=validate.Length(min=10))

    task_type = fields.Str(required=True, validate=validate.OneOf([
        "classification", "regression", "clustering", "nlp", "computer_vision"
    ]))

    primary_metric = fields.Str(required=True, validate=validate.OneOf([
        "accuracy", "f1_score", "precision", "recall", "auc_roc",
        "log_loss", "rmse", "mae", "r2", "mape"
    ]))

    start_date = fields.DateTime(required=True)
    end_date   = fields.DateTime(required=True)

    # Champs optionnels
    problem_statement      = fields.Str(load_default=None)
    rules                  = fields.Str(load_default=None)
    data_description       = fields.Str(load_default=None)
    evaluation_description = fields.Str(load_default=None)
    banner_url             = fields.Url(load_default=None)

    registration_start = fields.DateTime(load_default=None)
    results_date       = fields.DateTime(load_default=None)

    secondary_metrics = fields.List(fields.Str(), load_default=None)
    prizes            = fields.List(fields.Dict(), load_default=None)
    faq               = fields.List(fields.Dict(), load_default=None)
    evaluation_config = fields.Dict(load_default=None)
    allowed_formats   = fields.List(fields.Str(), load_default=None)

    max_submissions_per_day   = fields.Int(load_default=10, validate=validate.Range(min=1, max=100))
    max_submissions_total     = fields.Int(load_default=50, validate=validate.Range(min=1, max=1000))
    max_file_size_mb          = fields.Int(load_default=500, validate=validate.Range(min=1, max=5000))
    execution_timeout_seconds = fields.Int(load_default=120, validate=validate.Range(min=10, max=3600))

    @validates_schema
    def validate_dates(self, data, **kwargs):
        """Vérifie que end_date est postérieure à start_date."""
        start = data.get("start_date")
        end   = data.get("end_date")
        if start and end and end <= start:
            raise ValidationError(
                "La date de clôture doit être postérieure à la date de début.",
                field_name="end_date"
            )
