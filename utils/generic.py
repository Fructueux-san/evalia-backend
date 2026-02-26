from os import environ
import requests
from confs.main import logger

def allowed_file(filename: str, allowed_extendions: list):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extendions



def send_event_to_client(user_id, data: dict, msg_type: str, enabled: bool):
    """
    Envoie un évènement sse à un client. 
    Cette fonction est écrit pour principalement 
    envoyer les évenements depuis un processus celery
    vers l'app principale.
    """
    if environ.get("TESTING", None) == "test":
        logger.info("SSE not send because app in testing mode")
    else:
        if enabled:
            try:
                url = f"http://localhost:{environ.get('SSE_PORT')}/notify?user={user_id}&type={msg_type}"
                response = requests.post(f"{url}", json=data)
                return response
            except Exception as e: 
                logger.error("Impossible d'envoyer de notification, l'application SSE est peut-être en mode test ou inaccessible.")
