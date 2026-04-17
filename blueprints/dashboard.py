"""
Blueprint Dashboard — agrégation des données utilisateur pour la vue d'ensemble.
Préfixe : /api

Routes :
  GET   /api/dashboard/me  — Vue d'ensemble de l'utilisateur (JWT requis)
"""

from flask import Blueprint, jsonify
from flask_jwt_extended import get_jwt_identity, jwt_required
from flasgger import swag_from
from models.user import User
from models.competition import Competition, participations
from models.submission import Submission
from confs.main import db

dashboard_bp = Blueprint("dashboard", __name__)

@dashboard_bp.route("/dashboard/me", methods=["GET"])
@swag_from("/app/docs/dashboard/me.yaml")
@jwt_required()
def get_dashboard():
    """Retourne une vue agrégée pour le dashboard de l'utilisateur."""
    user_id = get_jwt_identity()
    user = User.query.get(user_id)

    if not user:
        return jsonify({"message": "Utilisateur introuvable"}), 404

    # 1. Infos utilisateur
    user_info = {
        "id":         str(user.id),
        "username":   user.username,
        "name":       user.name,
        "email":      user.email,
        "is_admin":   user.is_admin,
        "created_at": user.created_at.isoformat() if user.created_at else None,
    }

    # 2. Compétitions rejointes
    joined_competitions = [c.to_public_dict() for c in user.participations_list]

    # 3. Compétitions créées
    created_competitions = [c.to_public_dict() for c in user.created_competitions]

    # 4. Statistiques
    total_submissions = Submission.query.filter_by(user_id=user_id).count()
    
    # On pourrait ajouter d'autres stats ici (ex: meilleur score par compétition)
    
    return jsonify({
        "user": user_info,
        "competitions": {
            "joined": {
                "count": len(joined_competitions),
                "list": joined_competitions
            },
            "created": {
                "count": len(created_competitions),
                "list": created_competitions
            }
        },
        "stats": {
            "total_submissions": total_submissions
        }
    }), 200
