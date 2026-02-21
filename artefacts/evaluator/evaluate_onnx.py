import pandas as pd
import onnxruntime as ort
import json
import sys
import os
import numpy as np
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score

def evaluate():
    try:
        model_path = '/app/model.onnx'
        data_path = '/app/truth.csv'

        if not os.path.exists(model_path) or not os.path.exists(data_path):
            print(json.dumps({"error": "Fichiers ONNX manquants"}))
            sys.exit(1)

        # 1. Chargement des données
        df = pd.read_csv(data_path)
        X_test = df.iloc[:, :-1].values.astype(np.float32)
        y_true = df.iloc[:, -1].values

        # 2. Initialisation de la session ONNX
        session = ort.InferenceSession(model_path)
        input_name = session.get_inputs()[0].name

        # 3. Inférence
        # ONNX retourne une liste de sorties
        raw_preds = session.run(None, {input_name: X_test})[0]
        
        # Post-processing simple pour classification
        if raw_preds.ndim > 1 and raw_preds.shape[1] > 1:
            y_pred = np.argmax(raw_preds, axis=1)
        else:
            y_pred = (raw_preds > 0.5).astype(int).flatten()

        # 4. Métriques
        results = {
            "accuracy": float(accuracy_score(y_true, y_pred)),
            "precision": float(precision_score(y_true, y_pred, average='weighted', zero_division=0)),
            "recall": float(recall_score(y_true, y_pred, average='weighted', zero_division=0)),
            "f1_score": float(f1_score(y_true, y_pred, average='weighted', zero_division=0)),
            "framework": "onnx",
            "status": "success"
        }
        print(json.dumps(results))

    except Exception as e:
        print(json.dumps({"status": "error", "framework": "onnx", "error": str(e)}))
        sys.exit(1)

if __name__ == "__main__":
    evaluate()
