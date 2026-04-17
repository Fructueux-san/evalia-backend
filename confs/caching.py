import redis
from os import environ

url_string_sse = f"redis://:{environ.get('REDIS_PASSWORD')}@{environ.get('REDIS_HOST')}:{environ.get('REDIS_PORT')}/{environ.get('SSE_CACHE_DB')}"

def get_cache_connection(db=1, decode_responses=True):
    """
    Récupère une connection sur la base de donnée redis de l'app. 
    Quand la base n'est pas spécifié, on utilise le 1
    (redis donne 16 bases par instance [0 - 15])

    """
    # TODO: Baser la connexion sur un mécanise de pool
    
    redis_db = redis.StrictRedis(
        host=f"{environ.get('REDIS_HOST')}",
        port=int(f"{environ.get('REDIS_PORT')}"), 
        db=db, 
        decode_responses=decode_responses,
        password=f"{environ.get('REDIS_PASSWORD')}",
        encoding="utf-8"
    )
    return redis_db


