
from functools import wraps
from flask import jsonify, request, g



def is_logged_in(func):
    """
    Vérifie l'utilisateur connecté dans le 
    champs 'Authorization' de la requête. 
    Quand il est vérifier, les informations de l'utilisateur
    sont accessible dans le contexte global de la requête 
    avec l'objet 'g' de flask.
    """
    @wraps(func)
    def check_user_login(*args, **kwargs):
        authorization = request.headers.get("Authorization")

        if authorization:
            _token = str(authorization).split(' ')[1]
            # TODO: Faire les checking qu'il faut. 
            # A ne pas forcément utiliser
            return func(*args, **kwargs)

        else:
            return jsonify(message="Connexion nécéssaire pour accéder à la ressource"), 401
    return check_user_login

