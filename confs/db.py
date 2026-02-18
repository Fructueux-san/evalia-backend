from flasgger.utils import sys
from psycopg2 import DatabaseError
from psycopg2.pool import ThreadedConnectionPool
from os import environ


# Pour ne pas utiliser l'ORM
# connection direct par pool. 

# 1. Récupérer une connection de la pool
# 2. créer le curseur et exécuter la requête
# 3. fermer le cursor et remettre la connexion dans le pool

class Database:
    _db_pool: ThreadedConnectionPool
    def __init__(self, minconn=2, maxconn=60) -> None:

        try:
            self._db_pool = ThreadedConnectionPool(
                minconn=minconn, 
                maxconn=maxconn,
                user=environ.get("DATABASE_USER"),
                password=environ.get("DATABASE_PASSWORD"), 
                host=environ.get("DATABASE_HOST"), 
                port=environ.get("DATABASE_PORT"), 
                database=environ.get("DATABASE_NAME"),
                options=f"-c search_path=${environ.get('DATABASE_SCHEMAS', 'public')}"
            )
            # if self._db_pool:
            #     print("Successfully connected to the database")
        except (Exception, DatabaseError):
            print("Error when trying to connect to the database.")
            sys.exit(1)


    def get_instance(self) -> ThreadedConnectionPool: 
        return self._db_pool
