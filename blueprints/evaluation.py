# Endpoint concernant l'évalutation d'un modèle

from datetime import datetime
import os
from flasgger import swag_from
from flask import Blueprint, request, jsonify
from flask_jwt_extended import get_jwt_identity, jwt_required
from werkzeug.utils import secure_filename
from confs.main import db
from confs.main import celery
from models.submission import Submission
from utils.generic import allowed_file

from celery.result import AsyncResult



eval_bp = Blueprint("evaluation", __name__)

ALLOWED_MODELS = {'h5', 'pkl', 'pt', 'onnx'}
UPLOAD_FOLDER = '/app/uploads'


@eval_bp.route("/eval/all-type", methods=["GET"])
@swag_from("/app/docs/submission/available.yaml")
def les_type_d_evaluation_existants():
    return jsonify({
        'sklearn': 'scikit_learn_evaluation',
        'tensorflow': 'tensorflow_evaluation',
        'onnx': 'onnx_evaluation',
        'pytorch': 'pytorch_evaluation'
    }), 200

@eval_bp.route("/eval/<uuid:comp_id>/submit", methods=["POST"])
@swag_from("/app/docs/evaluation/send.yaml")
@jwt_required()
def evaluation_model(comp_id):
    if 'model_file' not in request.files:
        return jsonify({"error": "Fichier de modèle manquant"}), 400

    current_user_id = get_jwt_identity()
            
    file = request.files['model_file']
    user_id = request.form.get('user_id') 
    model_type = request.form.get('model_type') # 'sklearn', 'tensorflow', etc.

    if not model_type or model_type not in ['sklearn', 'tensorflow', 'onnx', 'pytorch']:
        return jsonify({'error': 'Type de modèle invalide ou manquant'}), 400
    
    # Vérification extension
    extension = file.filename.rsplit('.', 1)[1].lower()
    if extension not in ALLOWED_MODELS:
        return jsonify({"error": f"Extension .{extension} non supportée"}), 400

    # Sauvegarde physique
    save_dir = os.path.join(UPLOAD_FOLDER, 'submissions', str(comp_id), str(user_id))
    os.makedirs(save_dir, exist_ok=True)
    
    filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{secure_filename(file.filename)}"
    filepath = os.path.join(save_dir, filename)
    file.save(filepath)

    # Création de l'entrée en base
    new_submission = Submission(
        user_id=current_user_id,
        competition_id=comp_id,
        model_path=filepath,
        model_type=model_type, # On utilise le type formel
        status="pending"
    )
    
    db.session.add(new_submission)
    db.session.flush() # Pour récupérer l'ID sans commiter tout de suite si besoin
    db.session.commit()

    # Mapping des tâches Celery
    task_mapping = {
        'sklearn': 'scikit_learn_evaluation',
        'tensorflow': 'tensorflow_evaluation',
        'onnx': 'onnx_evaluation',
        'pytorch': 'pytorch_evaluation'
    }

    task_name = task_mapping.get(model_type)
    
    # ENVOI DE LA TACHE : On envoie l'ID (string) et non l'objet SQL
    task = celery.send_task(task_name, kwargs={
        'submission_id': str(new_submission.id),
        'model_path': filepath
    })

    return jsonify({
        "message": "Évaluation lancée",
        "submission_id": new_submission.id,
        "task_id": task.id,
        "status": "pending"
    }), 201


@eval_bp.route("/eval/status/<model_id>")
def status_d_evaluation():
    raise NotImplementedError
    
    
