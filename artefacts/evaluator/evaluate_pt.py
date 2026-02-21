import pandas as pd
import torch
import json
import sys
import os
import numpy as np
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score

def evaluate():
    try:
        model_path = '/app/model.pt'
        data_path = '/app/truth.csv'

        if not os.path.exists(model_path) or not os.path.exists(data_path):
            print(json.dumps({"error": "Fichiers manquants dans le conteneur PyTorch"}))
            sys.exit(1)

        # 1. Chargement des données
        df = pd.read_csv(data_path)
        X_test = torch.tensor(df.iloc[:, :-1].values).float()
        y_true = df.iloc[:, -1].values

        # 2. Chargement du modèle (Modèle complet sauvegardé)
        # On utilise map_location=torch.device('cpu') car le conteneur n'a pas de GPU
        model = torch.load(model_path, map_location=torch.device('cpu'))
        model.eval() 

        # 3. Inférence
        with torch.no_grad():
            outputs = model(X_test)
            # Gestion classification binaire (1 sortie) vs Multi-classe (n sorties)
            if outputs.shape[1] == 1:
                y_pred = (torch.sigmoid(outputs) > 0.5).int().numpy().flatten()
            else:
                _, y_pred = torch.max(outputs, 1)
                y_pred = y_pred.numpy()

        # 4. Métriques
        results = {
            "accuracy": float(accuracy_score(y_true, y_pred)),
            "precision": float(precision_score(y_true, y_pred, average='weighted', zero_division=0)),
            "recall": float(recall_score(y_true, y_pred, average='weighted', zero_division=0)),
            "f1_score": float(f1_score(y_true, y_pred, average='weighted', zero_division=0)),
            "framework": "pytorch",
            "status": "success"
        }
        print(json.dumps(results))

    except Exception as e:
        print(json.dumps({"status": "error", "framework": "pytorch", "error": str(e)}))
        sys.exit(1)

if __name__ == "__main__":
    evaluate()
