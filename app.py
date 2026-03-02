from blueprints.user import user_bp
from confs.main import app
from flask_cors import CORS
from flasgger import Swagger
from confs.swagger import swagger_config, swagger_template
from blueprints.competition import competition_bp
from blueprints.evaluation import eval_bp
from flask import request


CORS(app, resources={r"/*": {"origins": "*"}})

# la docs sera disponible sur /apidocs
Swagger(app, config=swagger_config, template=swagger_template)

# Pour qu'il y ai une prise en charge des migrations
from confs.main import db
from models import *


# Permetre à ce que les request OPTIONS soient acceptés depuis les origines
# et ajout d'autre headers pour éviter le CORS
@app.before_request
def catch_options():
    if request.method == "OPTIONS":
        response = app.make_default_options_response()
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type,Authorization"
        response.headers["Access-Control-Allow-Methods"] = "GET,PUT,POST,DELETE,OPTIONS"
        return response


@app.after_request
def add_cors_headers(response):

    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    response.headers['Content-Security-Policy'] = (
        "default-src 'self'; "
        "script-src 'self' https://apis.google.com 'unsafe-inline'; "
        "style-src 'self' https://fonts.googleapis.com 'unsafe-inline'; "
        "font-src 'self' https://fonts.gstatic.com; "
        "img-src 'self' data:; "
    )
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    response.headers['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=()'
    return response


# Quand vous créez un fichier de blueprint, venez l'enregistrer ici
app.register_blueprint(user_bp, url_prefix="/api")
app.register_blueprint(competition_bp, url_prefix="/api")
app.register_blueprint(eval_bp, url_prefix="/api")

if __name__ == "__main__":
    app.run(port=8000, host="0.0.0.0", debug=True)
