import os 
from flask import Blueprint, abort, request, jsonify, send_file
from werkzeug.utils import secure_filename
from confs.main import db

from models.competition import Competition
from uuid import uuid4

from utils.generic import allowed_file
from flasgger import swag_from

competition_bp = Blueprint("competitions", __name__)

UPLOAD_FOLDER = "storage/datasets"
ALLOWED_EXTENSIONS = ['csv', 'xlsx', 'json', 'parquet']

@competition_bp.route("/competitions", methods=["POST"])
@swag_from("/app/docs/competition/create.yaml")
def create_competition():
    if 'raw_dataset' not in request.files or 'processed_dataset' not in request.files:
        return jsonify({'error': "Deux fichier(raw et processed) sont requis"}), 400

    raw_file = request.files['raw_dataset']
    processed_file = request.files["processed_dataset"]

    name = request.form.get("name")
    creator_id = request.form.get('creator_id')

    if not name or not creator_id:
        return jsonify({"error": "Nom de la compétition et ID créateur manquants"}), 400

    # 3. Validation et Sauvegarde des fichiers
    if raw_file and allowed_file(f'{raw_file.filename}', ALLOWED_EXTENSIONS) and processed_file and allowed_file(f'{processed_file.filename}', ALLOWED_EXTENSIONS):
        
        # Création d'un dossier unique par compétition pour éviter les collisions
        comp_folder_id = str(uuid4())
        save_path = os.path.join(UPLOAD_FOLDER, comp_folder_id)
        os.makedirs(save_path, exist_ok=True)

        raw_filename = secure_filename(f"{raw_file.filename}")
        processed_filename = secure_filename(f"{processed_file.filename}")

        raw_path = os.path.join(save_path, f"raw_{raw_filename}")
        proc_path = os.path.join(save_path, f"proc_{processed_filename}")

        raw_file.save(raw_path)
        processed_file.save(proc_path)

        # 4. Enregistrement en base de données
        new_comp = Competition(
            name=name,
            description=request.form.get('description'),
            created_by=creator_id,
            raw_dataset_path=raw_path,
            processed_dataset_path=proc_path
        )

        db.session.add(new_comp)
        db.session.commit()

        return jsonify({"message": "Compétition créée", "id": new_comp.id}), 201

    return jsonify({"error": "Format de fichier non autorisé"}), 400




@competition_bp.route('/competitions/<uuid:id>/raw-dataset', methods=['GET'])
@swag_from("/app/docs/competition/download-raw-dataset.yaml")
def get_raw_dataset(id):
    """
    Récupère le dataset brut d'une compétition.
    """
    competition = Competition.query.get_or_404(id)
    
    if not competition.raw_dataset_path or not os.path.exists(competition.raw_dataset_path):
        abort(404, description="Fichier dataset brut introuvable.")

    return send_file(
        competition.raw_dataset_path,
        as_attachment=True,
        download_name=f"raw_data_{id}.csv" # Nom suggéré au navigateur
    )

@competition_bp.route('/competitions/<uuid:id>/processed-dataset', methods=['GET'])
@swag_from("/app/docs/competition/download-proceeded-dataset.yaml")
def get_processed_dataset(id):
    """
    Récupère le dataset traité. 
    Note: Cet endpoint devrait être réservé aux admins/organisateurs.
    """
    competition = Competition.query.get_or_404(id)
    
    if not competition.processed_dataset_path or not os.path.exists(competition.processed_dataset_path):
        abort(404, description="Fichier dataset traité introuvable.")

    return send_file(
        competition.processed_dataset_path,
        as_attachment=True,
        download_name=f"processed_data_{id}.csv"
    )
