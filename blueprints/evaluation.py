# Endpoint concernant l'évalutation d'un modèle

import os
from flask import Blueprint, request, jsonify
from werkzeug.utils import secure_filename
from confs.main import celery

from celery.result import AsyncResult



eval_bp = Blueprint("evaluation", __name__)

ALLOWED_EXTENDIONS = {'h5', 'pkl', 'pt', 'onnx'}
UPLOAD_FOLDER = '/app/upload'
HOST_PATH = os.getenv("HOST_UPLOAD_PATH")


def allowed_file(filename: str):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENDIONS

@eval_bp.route("/eval/all-type", methods=["GET"])
def les_type_d_evaluation_existants():
    raise NotImplementedError()
    #return jsonify({}), 200

@eval_bp.route("/eval", methods=["POST"])
def evaluation_model():

    # TODO : prendre l'ID websocket/SSE du client 
    # pour lui streamer l'exécution
    file = request.files.get("model")
    data = request.form.to_dict()

    if not file or not allowed_file(file.filename if file.filename is not None else ''):
        return jsonify({"error": "Extension non autorisée"}), 400

    filename = secure_filename(file.filename)
    internal_filepath = os.path.join(UPLOAD_FOLDER, filename)
    file.save(internal_filepath)


    # en fonction type, envoyer la task dans la queue
    model_type = data['model_type']
    if model_type == 'sklearn':
        task = celery.send_task("scikit_learn_evaluation", kwargs={
            'model_path': internal_filepath,
            'user_data': data,
            'competition_data': {}
        })
    elif model_type == "tensorflow":
        task = celery.send_task("tensorflow_evaluation", kwargs={
            'model_path': internal_filepath,
            'user_data': data,
            'competition_data': {}
        })
    elif model_type == "onnx":
        task = celery.send_task("onnx_evaluation", kwargs={
            'model_path': internal_filepath,
            'user_data': data,
            'competition_data': {}
        })
    elif model_type == "pytorch":
        task = celery.send_task("pytorch_evaluation", kwargs={
            'model_path': internal_filepath,
            'user_data': data,
            'competition_data': {}
        })
    else:
        os.unlink(internal_filepath)
        return jsonify({'message': 'Spécifier convenablement le type de modèle'}), 400

    task_data = AsyncResult(task)
    return jsonify(task_id=task, result=task_data.result, status=task_data.status), 200


@eval_bp.route("/eval/status/<model_id>")
def status_d_evaluation():
    raise NotImplementedError
    
    
