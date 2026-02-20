# Endpoint concernant l'évalutation d'un modèle

from flask import Blueprint, request, jsonify

eval_bp = Blueprint("evaluation", __name__)

@eval_bp.route("/eval/all-type", methods=["GET"])
def les_type_d_evaluation_existants():
    raise NotImplementedError()
    #return jsonify({}), 200

@eval_bp.route("/eval", methods=["POST"])
def evaluation_model():
    raise NotImplementedError


@eval_bp.route("/eval/status/<model_id>")
def status_d_evaluation():
    raise NotImplementedError
    
    
