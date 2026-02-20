from celery import shared_task

@shared_task(name="tensorflow_evaluation")
def run_evaluation(model_path, user_data, competition_data):
    # Faire une évaluation en utilisant scikit-learn


    # 1. On va charger les données que le participant n'a pas 


    # 2. charger le modèle soumis


    # 4 exporter le résultat au format standard
    return None 

