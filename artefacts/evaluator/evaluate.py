import pandas as pd
import joblib
import json
import sys
import os
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score

def evaluate():
    try:
        # 1. Chemins fixes définis par le montage des volumes Docker
        model_path = '/app/model.pkl'
        data_path = '/app/truth.csv'

        if not os.path.exists(model_path) or not os.path.exists(data_path):
            print(json.dumps({"error": "Fichiers manquants dans le conteneur"}))
            sys.exit(1)

        # 2. Chargement du dataset de vérité terrain
        # On part du principe que la dernière colonne est la cible (y)
        df = pd.read_csv(data_path)
        X_test = df.iloc[:, :-1]  # Toutes les colonnes sauf la dernière
        y_true = df.iloc[:, -1]   # La dernière colonne (labels)

        # 3. Chargement du modèle
        model = joblib.load(model_path)

        # 4. Inférence
        y_pred = model.predict(X_test)

        # 5. Calcul des métriques
        # On utilise 'weighted' pour gérer le multi-classe si nécessaire
        results = {
            "accuracy": float(accuracy_score(y_true, y_pred)),
            "precision": float(precision_score(y_true, y_pred, average='weighted', zero_division=0)),
            "recall": float(recall_score(y_true, y_pred, average='weighted', zero_division=0)),
            "f1_score": float(f1_score(y_true, y_pred, average='weighted', zero_division=0)),
            "status": "success"
        }

        # 6. Sortie standard pour récupération par Celery
        print(json.dumps(results))

    except Exception as e:
        print(json.dumps({
            "status": "error",
            "error": str(e)
        }))
        sys.exit(1)

if __name__ == "__main__":
    evaluate()
