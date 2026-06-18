"""
Blueprint Competitions — gestion des compétitions et des participations.
Préfixe : /api

Routes compétitions :
  POST   /api/competitions                      — Créer une compétition (JWT requis)
  GET    /api/competitions                      — Lister les compétitions publiques
  GET    /api/competitions/<id>                 — Détail d'une compétition
  PATCH  /api/competitions/<id>/status          — Changer le statut (admin)
  GET    /api/competitions/<id>/raw-dataset     — Télécharger le dataset brut
  GET    /api/competitions/<id>/processed-dataset — Télécharger le dataset traité (admin)

Routes participations :
  POST   /api/competitions/<id>/join            — Rejoindre une compétition (JWT requis)
  DELETE /api/competitions/<id>/leave           — Quitter une compétition (JWT requis)
  GET    /api/competitions/<id>/participants    — Liste des participants
  GET    /api/competitions/my                   — Compétitions du user connecté (JWT requis)
"""

import os
from flask import Blueprint, abort, request, jsonify, send_file
from werkzeug.utils import secure_filename
from flask_jwt_extended import jwt_required, get_jwt_identity
from marshmallow import ValidationError
from sqlalchemy.exc import SQLAlchemyError
from flasgger import swag_from

from confs.main import db, logger
from middlewares.auth import admin_required
from models.competition import Competition, CompetitionStatus, participations
from models.user import User
from validators.competition import CreateCompetitionSchema
from utils.generic import allowed_file

competition_bp = Blueprint("competitions", __name__)

# Chemin absolu pour que la sauvegarde (relative au cwd) et `send_file`
# (résolu relativement au root_path de l'app Flask) pointent vers le même
# emplacement, quel que soit le contexte d'exécution.
BASE_DIR           = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UPLOAD_FOLDER      = os.path.join(BASE_DIR, "storage", "datasets")
ALLOWED_EXTENSIONS = ["csv", "xlsx", "json", "parquet"]
ALLOWED_IMAGE_EXTENSIONS = ["png", "jpg", "jpeg", "webp", "gif"]


# ──────────────────────────────────────────────────────────────
#  POST /api/competitions
# ──────────────────────────────────────────────────────────────

@competition_bp.route("/competitions", methods=["POST"])
@swag_from("/app/docs/competition/create.yaml")
@jwt_required()
def create_competition():
    """Crée une nouvelle compétition (utilisateur connecté requis).

    Attend un formulaire multipart avec les champs de métadonnées
    et optionnellement les fichiers de datasets.
    """
    current_user_id = get_jwt_identity()

    # ── Validation des données du formulaire ──────────────────
    form_data = request.form.to_dict()
    # Conversion des champs JSON envoyés en string
    import json
    for field in ("prizes", "faq", "secondary_metrics", "allowed_formats"):
        if field in form_data and isinstance(form_data[field], str):
            try:
                form_data[field] = json.loads(form_data[field])
            except (ValueError, TypeError):
                pass

    try:
        validated = CreateCompetitionSchema().load(form_data)
    except ValidationError as err:
        return jsonify({"message": "Données invalides", "errors": err.messages}), 400

    # ── Vérification de l'unicité du slug ─────────────────────
    if Competition.query.filter_by(slug=validated["slug"]).first():
        return jsonify({"message": "Ce slug est déjà pris par une autre compétition"}), 409

    # ── Gestion des fichiers de datasets (optionnels) ─────────
    train_dataset_path = None
    test_dataset_path  = None

    raw_file       = request.files.get("raw_dataset")
    processed_file = request.files.get("processed_dataset")

    if raw_file:
        if not allowed_file(raw_file.filename, ALLOWED_EXTENSIONS):
            return jsonify({"error": "Format de fichier non autorisé pour raw_dataset"}), 400

        from uuid import uuid4
        comp_folder_id = str(uuid4())
        save_path = os.path.join(UPLOAD_FOLDER, comp_folder_id)
        os.makedirs(save_path, exist_ok=True)

        raw_filename       = secure_filename(raw_file.filename)
        train_dataset_path = os.path.join(save_path, f"raw_{raw_filename}")
        raw_file.save(train_dataset_path)

    if processed_file:
        if not allowed_file(processed_file.filename, ALLOWED_EXTENSIONS):
            return jsonify({"error": "Format de fichier non autorisé pour processed_dataset"}), 400

        if not train_dataset_path:
            from uuid import uuid4
            comp_folder_id = str(uuid4())
            save_path = os.path.join(UPLOAD_FOLDER, comp_folder_id)
            os.makedirs(save_path, exist_ok=True)

        proc_filename     = secure_filename(processed_file.filename)
        test_dataset_path = os.path.join(save_path, f"proc_{proc_filename}")
        processed_file.save(test_dataset_path)

    # ── Gestion de l'image de couverture (optionnelle) ────────
    banner_path = None
    banner_file = request.files.get("banner")

    if banner_file:
        if not allowed_file(banner_file.filename, ALLOWED_IMAGE_EXTENSIONS):
            return jsonify({"error": "Format d'image non autorisé pour banner"}), 400

        # Réutilise le dossier de la compétition si déjà créé par un dataset
        if not (train_dataset_path or test_dataset_path):
            from uuid import uuid4
            comp_folder_id = str(uuid4())
            save_path = os.path.join(UPLOAD_FOLDER, comp_folder_id)
            os.makedirs(save_path, exist_ok=True)

        banner_filename = secure_filename(banner_file.filename)
        banner_path     = os.path.join(save_path, f"banner_{banner_filename}")
        banner_file.save(banner_path)

    # ── Enregistrement en base de données ─────────────────────
    try:
        from models.competition import MetricName, TaskType
        competition = Competition(
            slug                    = validated["slug"],
            title                   = validated["title"],
            description             = validated["description"],
            task_type               = TaskType(validated["task_type"]),
            primary_metric          = MetricName(validated["primary_metric"]),
            start_date              = validated["start_date"],
            end_date                = validated["end_date"],
            created_by              = current_user_id,
            status                  = CompetitionStatus.DRAFT,
            # Champs optionnels
            problem_statement       = validated.get("problem_statement"),
            rules                   = validated.get("rules"),
            data_description        = validated.get("data_description"),
            evaluation_description  = validated.get("evaluation_description"),
            prizes                  = validated.get("prizes"),
            faq                     = validated.get("faq"),
            banner_url              = banner_path or validated.get("banner_url"),
            registration_start      = validated.get("registration_start"),
            results_date            = validated.get("results_date"),
            secondary_metrics       = validated.get("secondary_metrics"),
            evaluation_config       = validated.get("evaluation_config"),
            max_submissions_per_day = validated.get("max_submissions_per_day", 10),
            max_submissions_total   = validated.get("max_submissions_total", 50),
            max_file_size_mb        = validated.get("max_file_size_mb", 500),
            execution_timeout_seconds = validated.get("execution_timeout_seconds", 120),
            allowed_formats         = validated.get("allowed_formats", [".pkl", ".h5", ".pt", ".onnx"]),
            train_dataset_path      = train_dataset_path,
            test_dataset_path       = test_dataset_path,
        )

        db.session.add(competition)
        db.session.commit()

        return jsonify({
            "message": "Compétition créée avec succès",
            "id":      str(competition.id),
            "slug":    competition.slug,
        }), 201

    except SQLAlchemyError as err:
        db.session.rollback()
        logger.error(err)
        return jsonify({"message": "Erreur lors de la création de la compétition"}), 500


# ──────────────────────────────────────────────────────────────
#  GET /api/competitions
# ──────────────────────────────────────────────────────────────

@competition_bp.route("/competitions", methods=["GET"])
@swag_from("/app/docs/competition/list.yaml")
def list_competitions():
    """Retourne la liste des compétitions publiques (status != DRAFT)."""
    # Filtres optionnels via query params
    status_filter    = request.args.get("status")
    task_type_filter = request.args.get("task_type")
    page             = request.args.get("page", 1, type=int)
    per_page         = min(request.args.get("per_page", 20, type=int), 100)

    query = Competition.query.filter(
        Competition.status != CompetitionStatus.DRAFT
    )

    if status_filter:
        try:
            query = query.filter(Competition.status == CompetitionStatus(status_filter))
        except ValueError:
            return jsonify({"message": f"Statut '{status_filter}' invalide"}), 400

    if task_type_filter:
        from models.competition import TaskType
        try:
            query = query.filter(Competition.task_type == TaskType(task_type_filter))
        except ValueError:
            return jsonify({"message": f"Type de tâche '{task_type_filter}' invalide"}), 400

    query = query.order_by(Competition.created_at.desc())
    paginated = query.paginate(page=page, per_page=per_page, error_out=False)

    return jsonify({
        "competitions": [c.to_public_dict() for c in paginated.items],
        "pagination": {
            "page":       paginated.page,
            "per_page":   paginated.per_page,
            "total":      paginated.total,
            "pages":      paginated.pages,
            "has_next":   paginated.has_next,
            "has_prev":   paginated.has_prev,
        }
    }), 200


# ──────────────────────────────────────────────────────────────
#  GET /api/competitions/my
# ──────────────────────────────────────────────────────────────

@competition_bp.route("/competitions/my", methods=["GET"])
@swag_from("/app/docs/competition/my.yaml")
@jwt_required()
def get_my_competitions():
    """Retourne la liste des compétitions auxquelles l'utilisateur connecté participe."""
    user_id = get_jwt_identity()
    user = User.query.get(user_id)

    if not user:
        return jsonify({"message": "Utilisateur introuvable"}), 404

    # Filtres optionnels via query params
    status_filter    = request.args.get("status")
    task_type_filter = request.args.get("task_type")
    page             = request.args.get("page", 1, type=int)
    per_page         = min(request.args.get("per_page", 20, type=int), 100)

    query = Competition.query.join(
        participations
    ).filter(
        participations.c.user_id == user_id
    )

    if status_filter:
        try:
            query = query.filter(Competition.status == CompetitionStatus(status_filter))
        except ValueError:
            return jsonify({"message": f"Statut '{status_filter}' invalide"}), 400

    if task_type_filter:
        from models.competition import TaskType
        try:
            query = query.filter(Competition.task_type == TaskType(task_type_filter))
        except ValueError:
            return jsonify({"message": f"Type de tâche '{task_type_filter}' invalide"}), 400

    query = query.order_by(Competition.created_at.desc())
    paginated = query.paginate(page=page, per_page=per_page, error_out=False)

    return jsonify({
        "competitions": [c.to_public_dict() for c in paginated.items],
        "pagination": {
            "page":       paginated.page,
            "per_page":   paginated.per_page,
            "total":      paginated.total,
            "pages":      paginated.pages,
            "has_next":   paginated.has_next,
            "has_prev":   paginated.has_prev,
        }
    }), 200


# ──────────────────────────────────────────────────────────────
#  GET /api/competitions/<id>
# ──────────────────────────────────────────────────────────────

@competition_bp.route("/competitions/<uuid:id>", methods=["GET"])
@swag_from("/app/docs/competition/detail.yaml")
def get_competition(id):
    """Retourne les détails publics d'une compétition, enrichis des infos de participation si JWT présent."""
    from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity
    from models.submission import Submission

    competition = Competition.query.get_or_404(id, description="Compétition introuvable")
    data = competition.to_public_dict()

    # JWT optionnel : on tente de récupérer l'identité sans bloquer si absent
    current_user_id = None
    try:
        verify_jwt_in_request(optional=True)
        current_user_id = get_jwt_identity()
    except Exception:
        pass

    if current_user_id:
        user = User.query.get(current_user_id)
        is_joined = user in competition.participants if user else False

        my_best_score = None
        my_submissions_count = 0
        my_rank = None

        if is_joined:
            my_submissions_count = Submission.query.filter_by(
                user_id=current_user_id,
                competition_id=competition.id,
            ).count()

            best = (
                Submission.query
                .filter_by(user_id=current_user_id, competition_id=competition.id)
                .filter(Submission.score.isnot(None))
                .order_by(Submission.score.desc())
                .first()
            )
            my_best_score = best.score if best else None

        data["my_participation"] = {
            "is_joined":          is_joined,
            "my_best_score":      my_best_score,
            "my_submissions_count": my_submissions_count,
            "my_rank":            my_rank,  # calculé côté leaderboard
        }
    else:
        data["my_participation"] = None

    return jsonify(data), 200


# ──────────────────────────────────────────────────────────────
#  PUT /api/competitions/<id>
# ──────────────────────────────────────────────────────────────

@competition_bp.route("/competitions/<uuid:id>", methods=["PUT"])
@jwt_required()
def update_competition(id):
    """Met à jour les détails d'une compétition (créateur ou admin uniquement)."""
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    competition = Competition.query.get_or_404(id, description="Compétition introuvable")

    if str(competition.created_by) != current_user_id and (not user or not user.is_admin):
        return jsonify({"message": "Accès refusé"}), 403

    form_data = request.form.to_dict()
    import json
    for field in ("prizes", "faq", "secondary_metrics", "allowed_formats"):
        if field in form_data and isinstance(form_data[field], str):
            try:
                form_data[field] = json.loads(form_data[field])
            except (ValueError, TypeError):
                pass

    from validators.competition import UpdateCompetitionSchema
    try:
        validated = UpdateCompetitionSchema().load(form_data)
    except ValidationError as err:
        return jsonify({"message": "Données invalides", "errors": err.messages}), 400

    # Fichiers
    raw_file = request.files.get("raw_dataset")
    processed_file = request.files.get("processed_dataset")
    
    if raw_file or processed_file:
        from uuid import uuid4
        comp_folder_id = str(uuid4())
        save_path = os.path.join(UPLOAD_FOLDER, comp_folder_id)
        os.makedirs(save_path, exist_ok=True)

        if raw_file:
            if not allowed_file(raw_file.filename, ALLOWED_EXTENSIONS):
                return jsonify({"error": "Format non autorisé pour raw_dataset"}), 400
            raw_filename = secure_filename(raw_file.filename)
            competition.train_dataset_path = os.path.join(save_path, f"raw_{raw_filename}")
            raw_file.save(competition.train_dataset_path)

        if processed_file:
            if not allowed_file(processed_file.filename, ALLOWED_EXTENSIONS):
                return jsonify({"error": "Format non autorisé pour processed_dataset"}), 400
            proc_filename = secure_filename(processed_file.filename)
            competition.test_dataset_path = os.path.join(save_path, f"proc_{proc_filename}")
            processed_file.save(competition.test_dataset_path)

    # Mise à jour des champs
    for key, value in validated.items():
        if hasattr(competition, key):
            setattr(competition, key, value)

    try:
        db.session.commit()
        return jsonify({"message": "Compétition mise à jour", "id": str(competition.id)}), 200
    except SQLAlchemyError as err:
        db.session.rollback()
        logger.error(err)
        return jsonify({"message": "Erreur lors de la mise à jour"}), 500



# ──────────────────────────────────────────────────────────────
#  PATCH /api/competitions/<id>/status
# ──────────────────────────────────────────────────────────────

@competition_bp.route("/competitions/<uuid:id>/status", methods=["PATCH"])
@swag_from("/app/docs/competition/status.yaml")
@jwt_required()
@admin_required
def update_competition_status(id):
    """Change le statut d'une compétition (admin uniquement)."""
    competition = Competition.query.get_or_404(id, description="Compétition introuvable")

    data = request.get_json()
    new_status = data.get("status") if data else None

    if not new_status:
        return jsonify({"message": "Le champ 'status' est requis"}), 400

    try:
        competition.status = CompetitionStatus(new_status)
        db.session.commit()
        return jsonify({
            "message": "Statut mis à jour",
            "status":  competition.status.value,
        }), 200
    except ValueError:
        return jsonify({"message": f"Statut '{new_status}' invalide"}), 400
    except SQLAlchemyError as err:
        db.session.rollback()
        logger.error(err)
        return jsonify({"message": "Erreur lors de la mise à jour"}), 500


# ──────────────────────────────────────────────────────────────
#  POST /api/competitions/<id>/join
# ──────────────────────────────────────────────────────────────

@competition_bp.route("/competitions/<uuid:id>/join", methods=["POST"])
@swag_from("/app/docs/competition/join.yaml")
@jwt_required()
def join_competition(id):
    """Permet à un utilisateur connecté de rejoindre une compétition."""
    competition = Competition.query.get_or_404(id, description="Compétition introuvable")

    # La compétition doit accepter des inscriptions
    if competition.status not in (CompetitionStatus.UPCOMING, CompetitionStatus.ACTIVE):
        return jsonify({
            "message": "Cette compétition n'accepte pas de nouvelles inscriptions"
        }), 403

    user_id = get_jwt_identity()
    user = User.query.get(user_id)

    if not user:
        return jsonify({"message": "Utilisateur introuvable"}), 404

    # Vérifier si déjà inscrit
    if user in competition.participants:
        return jsonify({"message": "Vous êtes déjà inscrit à cette compétition"}), 409

    try:
        competition.participants.append(user)
        db.session.commit()

        return jsonify({
            "message":        "Inscription réussie",
            "competition_id": str(competition.id),
            "competition":    competition.title,
        }), 200

    except SQLAlchemyError as err:
        db.session.rollback()
        logger.error(err)
        return jsonify({"message": "Erreur lors de l'inscription"}), 500


# ──────────────────────────────────────────────────────────────
#  DELETE /api/competitions/<id>/leave
# ──────────────────────────────────────────────────────────────

@competition_bp.route("/competitions/<uuid:id>/leave", methods=["DELETE"])
@swag_from("/app/docs/competition/leave.yaml")
@jwt_required()
def leave_competition(id):
    """Permet à un utilisateur de quitter une compétition."""
    competition = Competition.query.get_or_404(id, description="Compétition introuvable")

    user_id = get_jwt_identity()
    user = User.query.get(user_id)

    if not user:
        return jsonify({"message": "Utilisateur introuvable"}), 404

    if user not in competition.participants:
        return jsonify({"message": "Vous n'êtes pas inscrit à cette compétition"}), 404

    try:
        competition.participants.remove(user)
        db.session.commit()
        return jsonify({"message": "Désinscription réussie"}), 200

    except SQLAlchemyError as err:
        db.session.rollback()
        logger.error(err)
        return jsonify({"message": "Erreur lors de la désinscription"}), 500


# ──────────────────────────────────────────────────────────────
#  GET /api/competitions/<id>/participants
# ──────────────────────────────────────────────────────────────

@competition_bp.route("/competitions/<uuid:id>/participants", methods=["GET"])
@swag_from("/app/docs/competition/participants.yaml")
def get_participants(id):
    """Retourne la liste des participants d'une compétition."""
    competition = Competition.query.get_or_404(id, description="Compétition introuvable")

    participants = [
        {
            "id":       str(u.id),
            "username": u.username,
            "name":     u.name,
        }
        for u in competition.participants
    ]

    return jsonify({
        "competition_id": str(competition.id),
        "title":          competition.title,
        "count":          len(participants),
        "participants":   participants,
    }), 200


# ──────────────────────────────────────────────────────────────
#  GET /api/competitions/<id>/raw-dataset
# ──────────────────────────────────────────────────────────────

@competition_bp.route("/competitions/<uuid:id>/raw-dataset", methods=["GET"])
@swag_from("/app/docs/competition/download-raw-dataset.yaml")
def get_raw_dataset(id):
    """Télécharge le dataset d'entraînement brut d'une compétition."""
    competition = Competition.query.get_or_404(id)

    if not competition.train_dataset_path or not os.path.exists(competition.train_dataset_path):
        abort(404, description="Fichier dataset brut introuvable.")

    return send_file(
        competition.train_dataset_path,
        as_attachment=True,
        download_name=f"raw_data_{id}.csv",
    )


# ──────────────────────────────────────────────────────────────
#  GET /api/competitions/<id>/processed-dataset
# ──────────────────────────────────────────────────────────────

@competition_bp.route("/competitions/<uuid:id>/processed-dataset", methods=["GET"])
@swag_from("/app/docs/competition/download-proceeded-dataset.yaml")
@jwt_required()
@admin_required
def get_processed_dataset(id):
    """Télécharge le dataset de vérité terrain (admin uniquement — jamais exposé publiquement)."""
    competition = Competition.query.get_or_404(id)

    if not competition.test_dataset_path or not os.path.exists(competition.test_dataset_path):
        abort(404, description="Fichier dataset traité introuvable.")

    return send_file(
        competition.test_dataset_path,
        as_attachment=True,
        download_name=f"processed_data_{id}.csv",
    )


# ──────────────────────────────────────────────────────────────
#  GET /api/competitions/<comp_id>/leaderboard
# ──────────────────────────────────────────────────────────────

@competition_bp.route("/competitions/<uuid:comp_id>/leaderboard", methods=["GET"])
@swag_from("/app/docs/competition/leaderboard.yaml")
def get_leaderboard(comp_id):
    """Retourne le classement d'une compétition.

    Paramètres de requête optionnels :
      - page / per_page : pagination du classement.
      - user_id         : retourne l'historique de progression de l'utilisateur
                          (toutes ses soumissions complétées dans l'ordre chronologique)
                          au lieu du classement global.
    """
    from models.submission import Submission

    competition = Competition.query.get_or_404(comp_id, description="Compétition introuvable")

    # Sens du tri selon la métrique principale (ex: RMSE → plus bas = mieux)
    higher_is_better = competition.primary_metric_info.get("higher_is_better", True)

    # ── Historique de progression d'un utilisateur ────────────
    user_filter = request.args.get("user_id")
    if user_filter:
        history = (
            Submission.query
            .filter_by(competition_id=comp_id, user_id=user_filter, status="completed")
            .filter(Submission.score.isnot(None))
            .order_by(Submission.created_at.asc())
            .all()
        )
        return jsonify({
            "competition_id": str(comp_id),
            "user_id":        user_filter,
            "metric":         competition.primary_metric.value,
            "count":          len(history),
            "history":        [s.to_dict() for s in history],
        }), 200

    # ── Classement global : meilleure soumission par utilisateur ─
    completed = (
        Submission.query
        .filter_by(competition_id=comp_id, status="completed")
        .filter(Submission.score.isnot(None))
        .all()
    )

    best_by_user = {}
    for sub in completed:
        uid = str(sub.user_id)
        current = best_by_user.get(uid)
        is_better = (
            current is None
            or (sub.score > current.score if higher_is_better else sub.score < current.score)
        )
        if is_better:
            best_by_user[uid] = sub

    ranked = sorted(best_by_user.values(), key=lambda s: s.score, reverse=higher_is_better)

    # ── Pagination ────────────────────────────────────────────
    page     = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 50, type=int), 100)
    start    = (page - 1) * per_page
    page_items = ranked[start:start + per_page]

    entries = []
    for offset, sub in enumerate(page_items):
        user = User.query.get(sub.user_id)
        entries.append({
            "rank":           start + offset + 1,
            "user": {
                "id":       str(sub.user_id),
                "username": user.username if user else None,
                "name":     user.name if user else None,
            },
            "score":          sub.score,
            "metrics_detail": sub.metrics_detail,
            "submission_id":  str(sub.id),
            "submitted_at":   sub.created_at.isoformat() if sub.created_at else None,
        })

    return jsonify({
        "competition_id":   str(comp_id),
        "competition":      competition.title,
        "metric":           competition.primary_metric.value,
        "higher_is_better": higher_is_better,
        "count":            len(ranked),
        "leaderboard":      entries,
        "pagination": {
            "page":     page,
            "per_page": per_page,
            "total":    len(ranked),
        },
    }), 200


# ──────────────────────────────────────────────────────────────
#  DELETE /api/competitions/<id>
# ──────────────────────────────────────────────────────────────

@competition_bp.route("/competitions/<uuid:id>", methods=["DELETE"])
@swag_from("/app/docs/competition/delete.yaml")
@jwt_required()
def delete_competition(id):
    """Supprime ou archive une compétition (créateur ou admin uniquement).

    Par défaut, la compétition est *archivée* (statut ARCHIVED).
    Passer le paramètre de requête `?hard=true` pour une suppression définitive.
    """
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    competition = Competition.query.get_or_404(id, description="Compétition introuvable")

    if str(competition.created_by) != current_user_id and (not user or not user.is_admin):
        return jsonify({"message": "Accès refusé"}), 403

    hard_delete = request.args.get("hard", "false").lower() == "true"

    try:
        if hard_delete:
            db.session.delete(competition)
            db.session.commit()
            return jsonify({"message": "Compétition supprimée définitivement"}), 200

        competition.status = CompetitionStatus.ARCHIVED
        db.session.commit()
        return jsonify({
            "message": "Compétition archivée",
            "status":  competition.status.value,
        }), 200

    except SQLAlchemyError as err:
        db.session.rollback()
        logger.error(err)
        return jsonify({"message": "Erreur lors de la suppression"}), 500