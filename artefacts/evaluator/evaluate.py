import pandas as pd
import joblib
import json
import sys
import numpy as np
import warnings
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    mean_squared_error, r2_score, mean_absolute_error
)

# On ignore les warnings pour garder un stdout propre (JSON uniquement)
warnings.filterwarnings("ignore")

def evaluate():
    try:
        model_path = '/app/model.pkl'
        data_path = '/app/truth.csv'

        # 1. Chargement des données
        df = pd.read_csv(data_path)
        # On sépare X et y (dernière colonne = cible)
        X_test = df.iloc[:, :-1].values 
        y_true = df.iloc[:, -1].values

        # 2. Chargement du modèle
        model = joblib.load(model_path)

        # 3. Inférence
        y_pred = model.predict(X_test)

        # 4. Détection automatique du type de tâche
        # Si les prédictions sont des entiers ou des chaînes, c'est de la classification
        # Si ce sont des flottants avec des décimales variées, c'est de la régression
        is_regression = False
        if np.issubdtype(y_pred.dtype, np.floating):
            # Vérification : si toutes les valeurs sont en réalité des entiers (ex: 1.0, 2.0)
            # on pourrait rester en classification, sinon -> régression
            if not np.all(np.mod(y_pred, 1) == 0):
                is_regression = True

        # 5. Calcul des métriques selon le type
        if is_regression:
            metrics = {
                "type": "regression",
                "mse": float(mean_squared_error(y_true, y_pred)),
                "rmse": float(np.sqrt(mean_squared_error(y_true, y_pred))),
                "mae": float(mean_absolute_error(y_true, y_pred)),
                "r2": float(r2_score(y_true, y_pred))
            }
        else:
            metrics = {
                "type": "classification",
                "accuracy": float(accuracy_score(y_true, y_pred)),
                "f1_weighted": float(f1_score(y_true, y_pred, average='weighted', zero_division=0)),
                "precision": float(precision_score(y_true, y_pred, average='weighted', zero_division=0)),
                "recall": float(recall_score(y_true, y_pred, average='weighted', zero_division=0))
            }

        # 6. Sortie JSON propre
        print(json.dumps(metrics))

    except Exception as e:
        # En cas d'erreur, on renvoie un JSON pour que Celery puisse le parser
        print(json.dumps({"status": "error", "error": str(e)}))
        sys.exit(1)

if __name__ == "__main__":
    evaluate()
