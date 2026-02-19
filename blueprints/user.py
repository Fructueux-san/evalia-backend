
from flask import Blueprint, jsonify, request
from flasgger import swag_from
from flask_jwt_extended import create_access_token
from flask_bcrypt import bcrypt

from models.user import User

user_bp = Blueprint("users", __name__)
@user_bp.get("/auth/user-info/<username>")
@swag_from("/app/docs/auth/user_info.yaml") # Chemin par rapport au conteneur docker
def username_informations(username: str):
    # Travailller avec un modèle ou un provider
    # pour récupérer le user 
    return jsonify({'username': f'{username}', 'name': "stanislas HOUETO"}), 200


@user_bp.route("/auth/login", methods=['POST'])
@swag_from("/app/docs/auth/login.yaml")
def login():
    data = request.get_json()
    username = data['username']
    password = data['password']

    print("Les data : ", username, password)

    user = User.query.filter_by(username=username).first()

    if user and bcrypt.checkpw(password, user.password):
        access_token = create_access_token(identity=user.id)
        return jsonify({'message': 'Login success', 'access_token': access_token}), 200
    else:
        return jsonify({'message': 'Login failed'}), 401
