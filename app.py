from os import environ
from blueprints.user import user_bp
from confs.main import app
from flask_cors import CORS
from flasgger import Swagger
from confs.swagger import swagger_config, swagger_template


CORS(app, resources={r"/*": {"origins": "*"}})

# la docs sera disponible sur /apidocs
Swagger(app, config=swagger_config, template=swagger_template)

# Pour qu'il y ai une prise en charge des migrations
from confs.main import db
from models import *


# Quand vous créez un fichier de blueprint, venez l'enregistrer ici
app.register_blueprint(user_bp, url_prefix="/api")

if __name__ == "__main__":
    app.run(port=8000, host="0.0.0.0", debug=True)
