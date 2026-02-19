from flask import Flask
from flask_sqlalchemy import SQLAlchemy 
from flask_migrate import Migrate
from os import environ
from sqlalchemy.orm import DeclarativeBase

from flask_jwt_extended import JWTManager, create_access_token

from confs.db import Database

app = Flask(__name__)

####### les configs de la DB #########
class Base(DeclarativeBase):
    pass

db_ = {}
db_user = environ.get('DATABASE_USER')
db_password = environ.get('DATABASE_PASSWORD')
db_host = environ.get('DATABASE_HOST')
db_port = environ.get('DATABASE_PORT')
db_name = environ.get('DATABASE_NAME')

app.config["SQLALCHEMY_DATABASE_URI"] = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"

app.config['SQLALCHEMY_TRACK_MODIFICATION'] = False

db = SQLAlchemy(app)
migrate = Migrate(app, db)


_db_conn = Database()

# Récupérer les instance de connexion ici si voulu
_db = _db_conn.get_instance()
######## Fin configs DB #########


##### LE JWT ########
app.config["SECRET_KEY"] = environ.get("APP_SECRET_KEY")
app.config["JWT_SECRET_KEY"] = environ.get("JWT_SECRET_KEY")
app.config['JWT_TOKEN_LOCATION'] = ['headers']
JWTManager(app)
