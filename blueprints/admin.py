"""
Blueprint Admin — supervision et administration de la plateforme.
Préfixe : /api  (toutes les routes nécessitent un JWT + droits administrateur)

Routes :
  GET   /api/admin/users                 — Lister les utilisateurs (pagination + filtres)
  PATCH /api/admin/users/<user_id>       — Modifier le rôle / le statut d'un utilisateur
  GET   /api/admin/competitions          — Vue d'ensemble de toutes les compétitions
  GET   /api/admin/submissions           — Superviser toutes les soumissions
  GET   /api/admin/logs                  — Journaux d'exécution (conteneur Docker)
  GET   /api/admin/system                — État des ressources système et conteneurs Docker
"""

import os
import shutil

from flask import Blueprint, request, jsonify
from flasgger import swag_from
from flask_jwt_extended import jwt_required
from sqlalchemy import or_
from sqlalchemy.exc import SQLAlchemyError

from confs.main import db, logger
from middlewares.auth import admin_required
from models.user import User
from models.competition import Competition
from models.submission import Submission

admin_bp = Blueprint("admin", __name__)


# ──────────────────────────────────────────────────────────────
#  Helpers
# ──────────────────────────────────────────────────────────────

def _user_dict(user):
    """Sérialisation d'un utilisateur pour les vues admin."""
    return {
        "id":         str(user.id),
        "username":   user.username,
        "name":       user.name,
        "email":      user.email,
        "is_admin":   user.is_admin,
        "is_active":  user.is_active,
        "created_at": user.created_at.isoformat() if user.created_at else None,
    }


def _parse_bool(value):
    """Convertit une valeur de query param en booléen, ou None si absente."""
    if value is None:
        return None
    return str(value).lower() in ("true", "1", "yes", "on")


# ──────────────────────────────────────────────────────────────
#  GET /api/admin/users
# ──────────────────────────────────────────────────────────────

@admin_bp.route("/admin/users", methods=["GET"])
@swag_from("/app/docs/admin/users_list.yaml")
@jwt_required()
@admin_required
def list_users():
    """Liste tous les utilisateurs avec pagination et filtres."""
    page     = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 20, type=int), 100)
    search   = request.args.get("search")
    is_admin = _parse_bool(request.args.get("is_admin"))
    is_active = _parse_bool(request.args.get("is_active"))

    query = User.query

    if search:
        like = f"%{search}%"
        query = query.filter(or_(
            User.username.ilike(like),
            User.email.ilike(like),
            User.name.ilike(like),
        ))
    if is_admin is not None:
        query = query.filter(User.is_admin == is_admin)
    if is_active is not None:
        query = query.filter(User.is_active == is_active)

    paginated = query.paginate(page=page, per_page=per_page, error_out=False)

    return jsonify({
        "users": [_user_dict(u) for u in paginated.items],
        "pagination": {
            "page":     paginated.page,
            "per_page": paginated.per_page,
            "total":    paginated.total,
            "pages":    paginated.pages,
            "has_next": paginated.has_next,
            "has_prev": paginated.has_prev,
        },
    }), 200


# ──────────────────────────────────────────────────────────────
#  PATCH /api/admin/users/<user_id>
# ──────────────────────────────────────────────────────────────

@admin_bp.route("/admin/users/<uuid:user_id>", methods=["PATCH"])
@swag_from("/app/docs/admin/users_update.yaml")
@jwt_required()
@admin_required
def update_user(user_id):
    """Modifie le rôle (is_admin) ou le statut (is_active — suspension) d'un utilisateur."""
    if not request.is_json:
        return jsonify({"message": "Le Content-Type doit être application/json"}), 415

    user = User.query.get(user_id)
    if not user:
        return jsonify({"message": "Utilisateur introuvable"}), 404

    data = request.get_json() or {}

    if "is_admin" in data:
        user.is_admin = bool(data["is_admin"])
    if "is_active" in data:
        user.is_active = bool(data["is_active"])

    try:
        db.session.commit()
        return jsonify({"message": "Utilisateur mis à jour", "user": _user_dict(user)}), 200
    except SQLAlchemyError as err:
        db.session.rollback()
        logger.error(err)
        return jsonify({"message": "Erreur lors de la mise à jour"}), 500


# ──────────────────────────────────────────────────────────────
#  GET /api/admin/competitions
# ──────────────────────────────────────────────────────────────

@admin_bp.route("/admin/competitions", methods=["GET"])
@swag_from("/app/docs/admin/competitions_list.yaml")
@jwt_required()
@admin_required
def list_all_competitions():
    """Vue d'ensemble de toutes les compétitions (tous statuts, y compris DRAFT/ARCHIVED)."""
    from models.competition import CompetitionStatus, TaskType

    page          = request.args.get("page", 1, type=int)
    per_page      = min(request.args.get("per_page", 20, type=int), 100)
    status_filter = request.args.get("status")
    task_filter   = request.args.get("task_type")

    query = Competition.query

    if status_filter:
        try:
            query = query.filter(Competition.status == CompetitionStatus(status_filter))
        except ValueError:
            return jsonify({"message": f"Statut '{status_filter}' invalide"}), 400
    if task_filter:
        try:
            query = query.filter(Competition.task_type == TaskType(task_filter))
        except ValueError:
            return jsonify({"message": f"Type de tâche '{task_filter}' invalide"}), 400

    query = query.order_by(Competition.created_at.desc())
    paginated = query.paginate(page=page, per_page=per_page, error_out=False)

    return jsonify({
        "competitions": [c.to_admin_dict() for c in paginated.items],
        "pagination": {
            "page":     paginated.page,
            "per_page": paginated.per_page,
            "total":    paginated.total,
            "pages":    paginated.pages,
            "has_next": paginated.has_next,
            "has_prev": paginated.has_prev,
        },
    }), 200


# ──────────────────────────────────────────────────────────────
#  GET /api/admin/submissions
# ──────────────────────────────────────────────────────────────

@admin_bp.route("/admin/submissions", methods=["GET"])
@swag_from("/app/docs/admin/submissions_list.yaml")
@jwt_required()
@admin_required
def list_all_submissions():
    """Liste toutes les soumissions de la plateforme (filtres : status, competition_id, user_id)."""
    page           = request.args.get("page", 1, type=int)
    per_page       = min(request.args.get("per_page", 20, type=int), 100)
    status_filter  = request.args.get("status")
    competition_id = request.args.get("competition_id")
    user_id        = request.args.get("user_id")

    query = Submission.query

    if status_filter:
        query = query.filter(Submission.status == status_filter)
    if competition_id:
        query = query.filter(Submission.competition_id == competition_id)
    if user_id:
        query = query.filter(Submission.user_id == user_id)

    query = query.order_by(Submission.created_at.desc())
    paginated = query.paginate(page=page, per_page=per_page, error_out=False)

    return jsonify({
        "submissions": [s.to_dict() for s in paginated.items],
        "pagination": {
            "page":     paginated.page,
            "per_page": paginated.per_page,
            "total":    paginated.total,
            "pages":    paginated.pages,
            "has_next": paginated.has_next,
            "has_prev": paginated.has_prev,
        },
    }), 200


# ──────────────────────────────────────────────────────────────
#  GET /api/admin/system
# ──────────────────────────────────────────────────────────────

@admin_bp.route("/admin/system", methods=["GET"])
@swag_from("/app/docs/admin/system.yaml")
@jwt_required()
@admin_required
def system_status():
    """Retourne l'état des ressources système et des conteneurs Docker.

    Robuste : si Docker n'est pas accessible, le champ `containers` contient l'erreur
    sans faire échouer la requête.
    """
    info = {}

    # ── Charge CPU ────────────────────────────────────────────
    try:
        load1, load5, load15 = os.getloadavg()
        info["load_average"] = {"1m": load1, "5m": load5, "15m": load15}
    except (OSError, AttributeError):
        info["load_average"] = None

    # ── Mémoire (/proc/meminfo) ───────────────────────────────
    try:
        mem = {}
        with open("/proc/meminfo", "r") as f:
            for line in f:
                key, _, rest = line.partition(":")
                mem[key.strip()] = rest.strip()
        info["memory"] = {
            "total": mem.get("MemTotal"),
            "free":  mem.get("MemFree"),
            "available": mem.get("MemAvailable"),
        }
    except OSError:
        info["memory"] = None

    # ── Disque ────────────────────────────────────────────────
    try:
        total, used, free = shutil.disk_usage("/")
        info["disk"] = {"total": total, "used": used, "free": free}
    except OSError:
        info["disk"] = None

    # ── Conteneurs Docker ─────────────────────────────────────
    containers = []
    try:
        import docker
        client = docker.from_env()
        for c in client.containers.list(all=True):
            containers.append({
                "id":     c.short_id,
                "name":   c.name,
                "status": c.status,
                "image":  c.image.tags[0] if c.image.tags else str(c.image.short_id),
            })
        info["containers"] = containers
    except Exception as err:  # docker indisponible / non monté
        info["containers"] = {"error": str(err)}

    return jsonify(info), 200


# ──────────────────────────────────────────────────────────────
#  GET /api/admin/logs
# ──────────────────────────────────────────────────────────────

@admin_bp.route("/admin/logs", methods=["GET"])
@swag_from("/app/docs/admin/logs.yaml")
@jwt_required()
@admin_required
def get_logs():
    """Retourne les derniers journaux d'un conteneur Docker.

    Paramètres : `container` (défaut: backend-evalia), `lines` (défaut: 100).
    Robuste : renvoie un message sans échouer si Docker est indisponible.
    """
    container_name = request.args.get("container", "backend-evalia")
    lines          = request.args.get("lines", 100, type=int)

    try:
        import docker
        client = docker.from_env()
        container = client.containers.get(container_name)
        raw = container.logs(tail=lines).decode("utf-8", errors="replace")
        return jsonify({
            "container": container_name,
            "lines":     lines,
            "logs":      raw.splitlines(),
        }), 200
    except Exception as err:
        return jsonify({
            "container": container_name,
            "logs":      [],
            "message":   f"Journaux indisponibles : {err}",
        }), 200
