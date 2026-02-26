"""
Blueprint Evaluation — soumission et suivi des modèles IA.
Préfixe : /api

Routes :
  GET   /api/eval/all-type                    — Types d'évaluation disponibles
  POST  /api/eval/<comp_id>/submit            — Soumettre un modèle (JWT requis)
  GET   /api/eval/status/<submission_id>      — Statut d'une soumission (JWT requis)
  GET   /api/eval/<comp_id>/submissions       — Mes soumissions pour une compétition (JWT requis)
"""

from datetime import datetime
import os
from flasgger import swag_from
from flask import Blueprint, request, jsonify
from flask_jwt_extended import get_jwt_identity, jwt_required
from werkzeug.utils import secure_filename

from confs.main import db, celery, logger
from models.submission import Submission
from models.competition import Competition
from utils.generic import allowed_file

from celery.result import AsyncResult


eval_bp = Blueprint("evaluation", __name__)

ALLOWED_MODELS = {"h5", "pkl", "pt", "onnx", "joblib"}
UPLOAD_FOLDER  = "/app/uploads"

# Mapping librairie → nom de la tâche Celery
TASK_MAPPING = {
    "sklearn":     "scikit_learn_evaluation",
    "tensorflow":  "tensorflow_evaluation",
    "onnx":        "onnx_evaluation",
    "pytorch":     "pytorch_evaluation",
}


# ──────────────────────────────────────────────────────────────
#  GET /api/eval/all-type
# ──────────────────────────────────────────────────────────────

@eval_bp.route("/eval/all-type", methods=["GET"])
@swag_from("/app/docs/evaluation/available.yaml")
def les_type_d_evaluation_existants():
    """Retourne les types de modèles supportés et leur tâche Celery associée."""
    return jsonify(TASK_MAPPING), 200


# ──────────────────────────────────────────────────────────────
#  POST /api/eval/<comp_id>/submit
# ──────────────────────────────────────────────────────────────

@eval_bp.route("/eval/<uuid:comp_id>/submit", methods=["POST"])
@swag_from("/app/docs/evaluation/send.yaml")
@jwt_required()
def evaluation_model(comp_id):
    """Soumet un fichier de modèle pour évaluation dans une compétition.

    Le fichier est sauvegardé sur disque, une entrée Submission est créée
    en base de données, puis une tâche Celery est lancée pour l'évaluation asynchrone.
    """
    # ── Vérifications préliminaires ───────────────────────────
    if "model_file" not in request.files:
        return jsonify({"error": "Fichier de modèle manquant"}), 400

    current_user_id = get_jwt_identity()
            
    file = request.files['model_file']
    user_id = request.form.get('user_id') 
    model_type = request.form.get('model_type') # 'sklearn', 'tensorflow', etc.

    if not model_type or model_type not in TASK_MAPPING:
        return jsonify({"error": f"Type de modèle invalide. Valeurs acceptées : {list(TASK_MAPPING.keys())}"}), 400

    # Validation de l'extension
    if not file.filename or "." not in file.filename:
        return jsonify({"error": "Nom de fichier invalide"}), 400

    extension = file.filename.rsplit(".", 1)[1].lower()
    if extension not in competition.allowed_formats and f".{extension}" not in competition.allowed_formats:
        return jsonify({"error": f"Extension .{extension} non supportée pour cette compétition"}), 400

    # ── Sauvegarde physique du fichier ────────────────────────
    save_dir = os.path.join(UPLOAD_FOLDER, "submissions", str(comp_id), str(current_user_id))
    os.makedirs(save_dir, exist_ok=True)

    filename = f"{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{secure_filename(file.filename)}"
    filepath = os.path.join(save_dir, filename)
    file.save(filepath)

    # ── Chemin relatif stocké en base ─────────────────────────
    db_file_path = os.path.join("uploads", "submissions", str(comp_id), str(current_user_id), filename)

    # ── Création de la soumission en base ─────────────────────
    new_submission = Submission(
        user_id        = current_user_id,
        competition_id = comp_id,
        model_path     = db_file_path,
        model_type     = model_type,
        status         = "pending",
    )

    db.session.add(new_submission)
    db.session.flush()   # On récupère l'ID sans commiter tout de suite
    db.session.commit()

    # ── Lancement de la tâche Celery ──────────────────────────
    task_name = TASK_MAPPING[model_type]
    task = celery.send_task(task_name, kwargs={"submission_id": str(new_submission.id)})

    logger.info(f"Tâche {task_name} lancée pour submission {new_submission.id} (task_id={task.id})")

    return jsonify({
        "message":       "Évaluation lancée",
        "submission_id": str(new_submission.id),
        "task_id":       task.id,
        "status":        "pending",
    }), 201


# ──────────────────────────────────────────────────────────────
#  GET /api/eval/status/<submission_id>
# ──────────────────────────────────────────────────────────────

@eval_bp.route("/eval/status/<uuid:submission_id>", methods=["GET"])
@swag_from("/app/docs/evaluation/status.yaml")
@jwt_required()
def statut_soumission(submission_id):
    """Retourne le statut d'une soumission : état en DB + état Celery en temps réel.

    Seul le propriétaire de la soumission ou un admin peut consulter le statut.
    """
    current_user_id = get_jwt_identity()

    submission = Submission.query.get(submission_id)
    if not submission:
        return jsonify({"error": "Soumission introuvable"}), 404

    # Contrôle d'accès : seul le propriétaire (ou admin) peut voir
    from models.user import User
    user = User.query.get(current_user_id)
    if str(submission.user_id) != current_user_id and (not user or not user.is_admin):
        return jsonify({"error": "Accès refusé"}), 403

    # ── Statut de base depuis la base de données ──────────────
    result = submission.to_dict()

    return jsonify(result), 200


# ──────────────────────────────────────────────────────────────
#  GET /api/eval/<comp_id>/submissions
# ──────────────────────────────────────────────────────────────

@eval_bp.route("/eval/<uuid:comp_id>/submissions", methods=["GET"])
@swag_from("/app/docs/evaluation/list.yaml")
@jwt_required()
def mes_soumissions(comp_id):
    """Retourne toutes les soumissions de l'utilisateur connecté pour une compétition donnée."""
    current_user_id = get_jwt_identity()

    competition = Competition.query.get_or_404(comp_id, description="Compétition introuvable")

    submissions = Submission.query.filter_by(
        user_id        = current_user_id,
        competition_id = comp_id,
    ).order_by(Submission.created_at.desc()).all()

    return jsonify({
        "competition_id": str(comp_id),
        "competition":    competition.title,
        "count":          len(submissions),
        "submissions":    [s.to_dict() for s in submissions],
    }), 200
