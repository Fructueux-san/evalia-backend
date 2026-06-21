import docker
import os
import json
from models.submission import Submission
from models.competition import Competition
from confs.main import db, app, logger
from utils.generic import send_event_to_client

client = docker.from_env()
HOST_STORAGE = os.environ.get("APP_STORAGE", "/var/evalia-data")

def evaluate_submission(submission_id, image_name, container_model_name):
    with app.app_context():
        # 1. On récupère la soumission depuis la DB via son ID
        submission = db.session.get(Submission, submission_id)
        if not submission:
            return f"Erreur: Soumission {submission_id} introuvable"
        
        # 2. On récupère la compétition liée pour avoir le CSV de vérité terrain
        competition = db.session.get(Competition, submission.competition_id)
        if not competition:
            submission.status = "failed"
            db.session.commit()
            return "Erreur: Compétition introuvable"

        # 3. On extrait les chemins enregistrés en base
        model_path_on_disk = submission.model_path
        truth_path_on_disk = competition.test_dataset_path

        if not truth_path_on_disk:
            submission.status = "failed"
            submission.metrics_detail = {"error": "Cette compétition ne dispose pas de dataset de test d'évaluation."}
            db.session.commit()
            send_event_to_client(
                submission.user_id,
                data={'result': 'Model cannot be executed', "error": "Vérité terrain manquante"},
                msg_type=submission.status,
                enabled=True
            )
            return "Erreur: test_dataset_path est vide ou None"

        # Nettoyage des chemins absolus internes du backend pour correspondre aux volumes de l'hôte
        if truth_path_on_disk.startswith("/app/"):
            truth_path_on_disk = truth_path_on_disk[5:]
        if model_path_on_disk.startswith("/app/"):
            model_path_on_disk = model_path_on_disk[5:]

        logger.info(f"Évaluation soumission {submission_id} - Image: {image_name} - Modèle: {model_path_on_disk} - Truth: {truth_path_on_disk}")

        submission.status = "processing"
        db.session.commit()

        try:
            # 4. Lancement du conteneur Docker
            container_output = client.containers.run(
                image=image_name,
                working_dir="/app",
                command=["python3", "evaluate.py"],
                volumes={
                    os.path.join(HOST_STORAGE, model_path_on_disk): {'bind': f'/app/{container_model_name}', 'mode': 'ro'},
                    os.path.join(HOST_STORAGE, truth_path_on_disk): {'bind': '/app/truth.csv', 'mode': 'ro'}
                },
                network_disabled=True,
                remove=True,
                stderr=True,
                mem_limit="256m",  # 256 Mo pour soutenir TF/PyTorch
                nano_cpus=1000000000  # Limite 1 CPU
            )

            # 5. Parsing des résultats
            results = json.loads(container_output.decode('utf-8'))
            
            # Gestion d'erreur interne du script d'évaluation
            if results.get("status") == "error" or "error" in results:
                raise Exception(results.get("error", "Erreur d'inférence dans le conteneur d'évaluation"))

            # Extraction dynamique du score principal basé sur primary_metric
            metric_name = competition.primary_metric.value if hasattr(competition.primary_metric, 'value') else str(competition.primary_metric)
            
            metric_keys = [metric_name.lower(), metric_name.upper(), "accuracy", "f1_score", "rmse", "mse", "r2", "f1_weighted"]
            score = None
            for key in metric_keys:
                if key in results:
                    score = results[key]
                    break
            
            submission.score = score
            submission.metrics_detail = results
            submission.status = "completed"
            send_event_to_client(
                submission.user_id,
                data={"raw": str(container_output), 'result': results},
                msg_type=submission.status,
                enabled=True
            )

        except Exception as e:
            logger.error(f"Erreur d'évaluation pour la soumission {submission_id} : {str(e)}")
            submission.status = "failed"
            submission.metrics_detail = {"error": str(e)}
            send_event_to_client(
                submission.user_id,
                data={'result': 'Model cannot be executed', "error": str(e)},
                msg_type=submission.status,
                enabled=True
            )

        db.session.commit()
        return f"Success for submission {submission_id}"
