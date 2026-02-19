
from os import environ
from flask import Blueprint, jsonify, request
from flasgger import swag_from
from flask_jwt_extended import create_access_token
from flask_bcrypt import bcrypt, Bcrypt
from marshmallow import ValidationError
from sqlalchemy.exc import SQLAlchemyError

from models.user import User
from validators.auth import RegisterSchema
from confs.main import bcrypt
from confs.main import db, logger

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

    if user and bcrypt.check_password_hash(user.password, password):
        access_token = create_access_token(identity=user.id)
        return jsonify({'message': 'Login success', 'access_token': access_token}), 200
    else:
        return jsonify({'message': 'Login failed'}), 401

@user_bp.route("/auth/register", methods=['POST'])
@swag_from("/app/docs/auth/register.yaml")
def register():
    data = request.get_json()

    try:
        validated = RegisterSchema().load(data)
    except ValidationError as err:
        return jsonify(message="Données invalides", errors=err.messages), 400

    try:
        user = User()
        user.name = data['name']
        user.email = data["email"]
        user.password = bcrypt.generate_password_hash(data['password']).decode('utf-8') #type: ignore
        user.username = data["username"]
        
        db.session.add(user)
        db.session.commit()
        return jsonify({'message': 'Utilisateur créé avec succès'}), 201
    except SQLAlchemyError as err:
        logger.error(err)
        if environ.get("ENV", "PROD") == 'DEV':
            return jsonify({'message': 'Une erreur s\'est produite',}), 500
        else:
            logger.error({"error_msg": err._message(), "error_code": err.code})
            return jsonify({'message': 'Une erreur s\'est produite', "error_msg": err._message(), "error_code": err.code,}), 500
        




