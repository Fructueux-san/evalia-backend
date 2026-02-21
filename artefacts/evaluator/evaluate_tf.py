import pandas as pd
import tensorflow as tf
import json
import sys
import os
import numpy as np

def evaluate():
    try:
        # 1. Chemins fixes (Montage Docker)
        # Note : TensorFlow peut lire un .h5 ou un répertoire de modèle
        model_path = '/app/model.h5' 
        data_path = '/app/truth.csv'

        if not os.path.exists(model_path) or not os.path.exists(data_path):
            print(json.dumps({"error": "Fichiers manquants dans le conteneur TF"}))
            sys.exit(1)

        # 2. Chargement du dataset
        df = pd.read_csv(data_path)
        X_test = df.iloc[:, :-1].values  # Conversion en array numpy pour TF
        y_true = df.iloc[:, -1].values

        # 3. Chargement du modèle TensorFlow
        model = tf.keras.models.load_model(model_path)

        # 4. Inférence (Prédiction)
        y_probs = model.predict(X_test)
        
        # Gestion du type de sortie (Binaire vs Multi-classe)
        # Si la sortie a une seule colonne (sigmoïde), on arrondit à 0 ou 1
        if y_probs.shape[1] == 1:
            y_pred = (y_probs > 0.5).astype(int).flatten()
        else:
            # Si multi-classe (softmax), on prend l'indice du max
            y_pred = np.argmax(y_probs, axis=1)

        # 5. Calcul des métriques avec Keras ou Numpy
        # On utilise numpy/sklearn pour la consistance avec ton API
        from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score

        results = {
            "accuracy": float(accuracy_score(y_true, y_pred)),
            "precision": float(precision_score(y_true, y_pred, average='weighted', zero_division=0)),
            "recall": float(recall_score(y_true, y_pred, average='weighted', zero_division=0)),
            "f1_score": float(f1_score(y_true, y_pred, average='weighted', zero_division=0)),
            "framework": "tensorflow",
            "status": "success"
        }

        # 6. Sortie JSON pour Celery
        print(json.dumps(results))

    except Exception as e:
        print(json.dumps({
            "status": "error",
            "framework": "tensorflow",
            "error": str(e)
        }))
        sys.exit(1)

if __name__ == "__main__":
    evaluate()
