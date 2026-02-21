from functools import wraps
from flask import jsonify
from flask_jwt_extended import get_jwt_identity
from models.user import User

# Il faut mettre le ce décorateur apres le décorateur @jwt_required()
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Récupère l'ID du user depuis le JWT
        user_id = get_jwt_identity()
        
        # Cherche l'utilisateur en base
        user = User.query.get(user_id)
        
        # Vérification : l'utilisateur existe et est admin
        if not user or not user.is_admin:
            return jsonify({"error": "Accès refusé. Droits administrateur requis."}), 403
        
        return f(*args, **kwargs)
    
    return decorated_function
