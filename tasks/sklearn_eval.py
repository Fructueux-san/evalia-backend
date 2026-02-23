import docker
import os
import json
from celery import shared_task
from models.submission import Submission
from models.competition import Competition
from confs.main import db, app

client = docker.from_env()

HOST_STORAGE = os.environ.get("APP_STORAGE", "/var/evalia-data")

@shared_task(name="scikit_learn_evaluation")
def run_scikit_evaluation(submission_id):

    with app.app_context():
    
        # 1. On récupère la soumission depuis la DB via son ID
        submission = Submission.query.get(submission_id)
        if not submission:
            return f"Erreur: Soumission {submission_id} introuvable"
        
        # 2. On récupère la compétition liée pour avoir le CSV de vérité terrain
        competition = Competition.query.get(submission.competition_id)
        if not competition:
            submission.status = "failed"
            db.session.commit()
            return "Erreur: Compétition introuvable"

        # 3. On extrait les chemins enregistrés en base
        # Ce sont les chemins vers les fichiers stockés sur le serveur
        model_path_on_disk = submission.model_path 
        truth_path_on_disk = competition.processed_dataset_path

        submission.status = "processing"
        db.session.commit()

        try:
            # 4. Lancement du conteneur Docker
            # On mappe les fichiers du disque vers l'intérieur du conteneur
            print("Model path on disk", os.path.join(HOST_STORAGE, model_path_on_disk))
            print("Data path on disk", os.path.join(HOST_STORAGE, truth_path_on_disk))
            container_output = client.containers.run(
                image="evaluator-sklearn:latest",
                working_dir="/app",
                command=["cat", "truth.csv"],
                volumes={
                    os.path.join(HOST_STORAGE, model_path_on_disk): {'bind': '/app/model.pkl', 'mode': 'ro'},
                    os.path.join(HOST_STORAGE, truth_path_on_disk): {'bind': '/app/truth.csv', 'mode': 'ro'}
                },
                network_disabled=True,
                remove=False,
                stderr=True
            )

            # 5. Parsing des résultats renvoyés par le conteneur
            # results = json.loads(container_output.decode('utf-8'))
            results = container_output.decode('utf-8')
            
            # Mise à jour des scores en base
            # submission.score = results.get('accuracy')
            submission.score = 0.9
            submission.metrics_detail = results
            submission.status = "completed"

        except Exception as e:
            submission.status = "failed"
            submission.metrics_detail = {"error": str(e)}
        
        db.session.commit()
        return f"Success for submission {submission_id}"
