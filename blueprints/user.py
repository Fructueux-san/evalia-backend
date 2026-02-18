
from flask import Blueprint, jsonify
from flasgger import swag_from

user_bp = Blueprint("users", __name__)
@user_bp.get("/auth/user-info/<username>")
@swag_from("/app/docs/auth/user_info.yaml") # Chemin par rapport au conteneur docker
def username_informations(username: str):
    # Travailller avec un modèle ou un provider
    # pour récupérer le user 
    return jsonify({'username': f'{username}', 'name': "stanislas HOUETO"}), 200

