"""
Blueprint Auth — endpoints d'authentification et gestion du profil utilisateur.
Préfixe : /api

Routes :
  POST  /api/auth/register          — Créer un compte
  POST  /api/auth/login             — Se connecter (retourne un token JWT)
  GET   /api/auth/me                — Profil de l'utilisateur connecté (JWT requis)
  GET   /api/auth/dashboard         — Tableau de bord de l'utilisateur connecté (JWT requis)
  GET   /api/auth/user-info/<username> — Informations publiques d'un utilisateur
"""

from os import environ
from flask import Blueprint, jsonify, request
from flasgger import swag_from
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from marshmallow import ValidationError
from sqlalchemy.exc import SQLAlchemyError

from models.user import User
from validators.auth import RegisterSchema, LoginSchema
from confs.main import bcrypt, db, logger

user_bp = Blueprint("users", __name__)


# ──────────────────────────────────────────────────────────────
#  GET /api/auth/user-info/<username>
# ──────────────────────────────────────────────────────────────

@user_bp.get("/auth/user-info/<username>")
@swag_from("/app/docs/auth/user_info.yaml")
def username_informations(username: str):
    """Retourne les informations publiques d'un utilisateur à partir de son username."""
    user = User.query.filter_by(username=username).first()

    if not user:
        return jsonify({"message": "Utilisateur introuvable"}), 404

    return jsonify({
        "id":       str(user.id),
        "username": user.username,
        "name":     user.name,
        "email":    user.email,
    }), 200


# ──────────────────────────────────────────────────────────────
#  POST /api/auth/login
# ──────────────────────────────────────────────────────────────

@user_bp.route("/auth/login", methods=["POST"])
@swag_from("/app/docs/auth/login.yaml")
def login():
    """Authentifie un utilisateur et retourne un token JWT."""
    if not request.is_json:
        return jsonify({"message": "Le Content-Type doit être application/json"}), 415

    data = request.get_json()

    # Validation des données entrantes
    try:
        validated = LoginSchema().load(data)
    except ValidationError as err:
        return jsonify({"message": "Données invalides", "errors": err.messages}), 400

    user = User.query.filter_by(username=validated["username"]).first()

    if user and bcrypt.check_password_hash(user.password, validated["password"]):
        # L'identité stockée dans le token est l'UUID de l'utilisateur (sous forme de string)
        access_token = create_access_token(identity=str(user.id))
        return jsonify({
            "message":      "Connexion réussie",
            "access_token": access_token,
            "user": {
                "id":       str(user.id),
                "username": user.username,
                "name":     user.name,
                "email":    user.email,
                "is_admin": user.is_admin,
            }
        }), 200

    return jsonify({"message": "Identifiants incorrects"}), 401


# ──────────────────────────────────────────────────────────────
#  POST /api/auth/register
# ──────────────────────────────────────────────────────────────

@user_bp.route("/auth/register", methods=["POST"])
@swag_from("/app/docs/auth/register.yaml")
def register():
    """Crée un nouveau compte utilisateur."""
    if not request.is_json:
        return jsonify({"message": "Le Content-Type doit être application/json"}), 415

    data = request.get_json()

    # Validation des données
    try:
        validated = RegisterSchema().load(data)
    except ValidationError as err:
        return jsonify({"message": "Données invalides", "errors": err.messages}), 400

    # Vérification de l'unicité du username et de l'email
    if User.query.filter_by(username=validated["username"]).first():
        return jsonify({"message": "Ce nom d'utilisateur est déjà pris"}), 409

    if User.query.filter_by(email=validated["email"]).first():
        return jsonify({"message": "Cet email est déjà utilisé"}), 409

    try:
        user = User()
        user.name     = validated["name"]
        user.email    = validated["email"]
        user.username = validated["username"]
        user.password = bcrypt.generate_password_hash(validated["password"]).decode("utf-8")  # type: ignore

        db.session.add(user)
        db.session.commit()

        return jsonify({"message": "Compte créé avec succès", "id": str(user.id)}), 201

    except SQLAlchemyError as err:
        db.session.rollback()
        logger.error(err)
        if environ.get("ENV", "PROD") == "DEV":
            return jsonify({"message": "Une erreur s'est produite", "detail": str(err)}), 500
        return jsonify({"message": "Une erreur s'est produite"}), 500


# ──────────────────────────────────────────────────────────────
#  GET /api/auth/me
# ──────────────────────────────────────────────────────────────

@user_bp.route("/auth/me", methods=["GET"])
@swag_from("/app/docs/auth/me.yaml")
@jwt_required()
def me():
    """Retourne le profil complet de l'utilisateur actuellement connecté."""
    user_id = get_jwt_identity()
    user = User.query.get(user_id)

    if not user:
        return jsonify({"message": "Utilisateur introuvable"}), 404

    return jsonify({
        "id":         str(user.id),
        "username":   user.username,
        "name":       user.name,
        "email":      user.email,
        "is_admin":   user.is_admin,
        "is_active":  user.is_active,
        "created_at": user.created_at.isoformat() if user.created_at else None,
    }), 200


# ──────────────────────────────────────────────────────────────
#  GET /api/auth/dashboard
# ──────────────────────────────────────────────────────────────

@user_bp.route("/auth/dashboard", methods=["GET"])
@swag_from("/app/docs/auth/dashboard.yaml")
@jwt_required()
def dashboard():
    """Retourne les statistiques du tableau de bord de l'utilisateur connecté."""
    from models.competition import Competition, CompetitionStatus
    from models.submission import Submission

    user_id = get_jwt_identity()
    user = User.query.get(user_id)

    if not user:
        return jsonify({"message": "Utilisateur introuvable"}), 404

    # ── Statistiques compétitions ─────────────────────────────
    joined_competitions = user.participations_list
    created_competitions = user.created_competitions

    competitions_active = sum(
        1 for c in joined_competitions if c.status == CompetitionStatus.ACTIVE
    )
    competitions_finished = sum(
        1 for c in joined_competitions if c.status == CompetitionStatus.FINISHED
    )

    # ── Statistiques soumissions ──────────────────────────────
    total_submissions = Submission.query.filter_by(user_id=user.id).count()

    best_submission = (
        Submission.query
        .filter_by(user_id=user.id, status="completed")
        .filter(Submission.score.isnot(None))
        .order_by(Submission.score.desc())
        .first()
    )

    # ── Activité récente ──────────────────────────────────────
    recent_competitions = sorted(
        joined_competitions, key=lambda c: c.created_at or "", reverse=True
    )[:5]

    recent_submissions = (
        Submission.query
        .filter_by(user_id=user.id)
        .order_by(Submission.created_at.desc())
        .limit(5)
        .all()
    )

    return jsonify({
        "user": {
            "id":       str(user.id),
            "username": user.username,
            "name":     user.name,
            "email":    user.email,
        },
        "stats": {
            "competitions_joined":   len(joined_competitions),
            "competitions_created":  len(created_competitions),
            "competitions_active":   competitions_active,
            "competitions_finished": competitions_finished,
            "total_submissions":     total_submissions,
            "best_submission":       best_submission.to_dict() if best_submission else None,
        },
        "recent_competitions": [
            {
                "id":     str(c.id),
                "title":  c.title,
                "slug":   c.slug,
                "status": c.status.value,
            }
            for c in recent_competitions
        ],
        "recent_submissions": [s.to_dict() for s in recent_submissions],
    }), 200
