"""
Seeds — Peupler la base de données avec des données initiales.

Script idempotent : vérifie si les données existent avant d'insérer.
Usage :
    python3 seeds.py
"""

import os
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import numpy as np
import pandas as pd
import joblib
from sklearn.linear_model import LinearRegression, LogisticRegression

from app import app
from confs.main import db, bcrypt
from models.user import User
from models.competition import Competition, CompetitionStatus, TaskType, MetricName
from models.submission import Submission


# ──────────────────────────────────────────────────────────────
#  Données de seed
# ──────────────────────────────────────────────────────────────

USERS = [
    {
        "name": "Admin Evalia",
        "username": "admin-evalia",
        "email": "admin@evalia.local",
        "password": "Admin123!",
        "is_admin": True,
        "is_active": True,
    },
    {
        "name": "Stan Hto",
        "username": "stan-hto",
        "email": "stan.hto@evalia.local",
        "password": "Stan123!",
        "is_admin": False,
        "is_active": True,
    },
    {
        "name": "Marie Dupont",
        "username": "marie-dupont",
        "email": "marie.dupont@evalia.local",
        "password": "Marie123!",
        "is_admin": False,
        "is_active": True,
    },
]

now = datetime.now(timezone.utc)

COMPETITIONS = [
    {
        "slug": "house-price-prediction",
        "title": "Prédiction du prix des maisons",
        "description": (
            "Prédisez le prix de vente de maisons résidentielles à partir de "
            "caractéristiques telles que la surface, le nombre de pièces, "
            "l'emplacement géographique et l'année de construction."
        ),
        "problem_statement": (
            "## Objectif\n\n"
            "Construisez un modèle de régression capable de prédire le prix "
            "de vente d'une maison avec la plus faible erreur possible.\n\n"
            "## Données\n\n"
            "Le dataset contient 1 460 observations avec 79 variables explicatives."
        ),
        "rules": (
            "- Maximum 5 soumissions par jour\n"
            "- Pas de données externes autorisées\n"
            "- Le modèle doit être reproductible"
        ),
        "task_type": TaskType.REGRESSION,
        "primary_metric": MetricName.RMSE,
        "secondary_metrics": ["mae", "r2"],
        "status": CompetitionStatus.ACTIVE,
        "start_date": now - timedelta(days=10),
        "end_date": now + timedelta(days=50),
        "results_date": now + timedelta(days=55),
        "max_submissions_per_day": 5,
        "max_submissions_total": 100,
    },
    {
        "slug": "sentiment-analysis-reviews",
        "title": "Analyse de sentiment — Avis clients",
        "description": (
            "Classifiez les avis clients en positif, négatif ou neutre. "
            "Le dataset contient des commentaires en français issus de "
            "plateformes e-commerce."
        ),
        "problem_statement": (
            "## Objectif\n\n"
            "Entraînez un classificateur NLP pour déterminer le sentiment "
            "exprimé dans un avis client.\n\n"
            "## Évaluation\n\n"
            "La métrique principale est le F1-Score macro-averaged."
        ),
        "rules": (
            "- Pré-entraînement autorisé (transformers, word2vec, etc.)\n"
            "- Maximum 10 soumissions par jour\n"
            "- Modèles ≤ 500 Mo"
        ),
        "task_type": TaskType.NLP,
        "primary_metric": MetricName.F1_SCORE,
        "secondary_metrics": ["accuracy", "precision", "recall"],
        "status": CompetitionStatus.UPCOMING,
        "start_date": now + timedelta(days=5),
        "end_date": now + timedelta(days=60),
        "results_date": now + timedelta(days=65),
        "max_submissions_per_day": 10,
        "max_submissions_total": 50,
    },
]


# ──────────────────────────────────────────────────────────────
#  Compétitions ÉVALUABLES (dataset de test + modèle + soumission)
# ──────────────────────────────────────────────────────────────

BASE_DIR     = os.path.dirname(os.path.abspath(__file__))
DATASETS_DIR = os.path.join(BASE_DIR, "storage", "datasets")


def _build_regression_dataset():
    """Génère un dataset de régression (area -> price) et entraîne un modèle sklearn."""
    rng   = np.random.default_rng(42)
    area  = rng.integers(1500, 4500, size=250)
    price = area * 150 + rng.normal(0, 10000, size=250) + 50000
    df = pd.DataFrame({"area": area, "price": price.round(2)})

    train = df.iloc[:200].reset_index(drop=True)
    truth = df.iloc[200:].reset_index(drop=True)

    model = LinearRegression()
    model.fit(train[["area"]], train["price"])
    return train, truth, model


def _build_classification_dataset():
    """Génère un dataset de classification binaire (f1, f2 -> label) et entraîne un modèle."""
    rng   = np.random.default_rng(7)
    feats = rng.normal(0, 1, size=(250, 2))
    label = (feats[:, 0] + feats[:, 1] > 0).astype(int)
    df = pd.DataFrame({
        "f1":    feats[:, 0].round(4),
        "f2":    feats[:, 1].round(4),
        "label": label,
    })

    train = df.iloc[:200].reset_index(drop=True)
    truth = df.iloc[200:].reset_index(drop=True)

    model = LogisticRegression()
    model.fit(train[["f1", "f2"]], train["label"])
    return train, truth, model


# Note : les chemins de datasets/modèles sont stockés en RELATIF pour rester
# compatibles avec le montage Docker des workers Celery
# (os.path.join(APP_STORAGE, chemin_relatif) côté hôte).
EVAL_COMPETITIONS = [
    {
        "slug":           "demo-eval-regression",
        "title":          "Démo évaluable — Régression (prix immobilier)",
        "description":    "Compétition de démonstration prête pour l'évaluation automatique (régression, métrique RMSE).",
        "task_type":      TaskType.REGRESSION,
        "primary_metric": MetricName.RMSE,
        "folder":         "seed-eval-regression",
        "builder":        _build_regression_dataset,
    },
    {
        "slug":           "demo-eval-classification",
        "title":          "Démo évaluable — Classification binaire",
        "description":    "Compétition de démonstration prête pour l'évaluation automatique (classification, métrique accuracy).",
        "task_type":      TaskType.CLASSIFICATION,
        "primary_metric": MetricName.ACCURACY,
        "folder":         "seed-eval-classification",
        "builder":        _build_classification_dataset,
    },
]


def seed_evaluation(admin_user, participant):
    """Crée des compétitions évaluables : dataset de test + modèle .pkl + soumission.

    Idempotent : ne recrée pas une compétition / soumission déjà présente.
    """
    created = 0
    now = datetime.now(timezone.utc)

    for cfg in EVAL_COMPETITIONS:
        # 1. Génération du dataset (train + vérité-terrain) et du modèle
        train_df, truth_df, model = cfg["builder"]()

        folder_abs = os.path.join(DATASETS_DIR, cfg["folder"])
        os.makedirs(folder_abs, exist_ok=True)
        train_df.to_csv(os.path.join(folder_abs, "train.csv"), index=False)
        truth_df.to_csv(os.path.join(folder_abs, "truth.csv"), index=False)

        train_rel = os.path.join("storage", "datasets", cfg["folder"], "train.csv")
        truth_rel = os.path.join("storage", "datasets", cfg["folder"], "truth.csv")

        # 2. Compétition (ACTIVE → soumissions ouvertes)
        competition = Competition.query.filter_by(slug=cfg["slug"]).first()
        if competition:
            print(f"  Compétition évaluable '{cfg['slug']}' existe déjà")
        else:
            competition = Competition(
                slug                    = cfg["slug"],
                title                   = cfg["title"],
                description             = cfg["description"],
                task_type               = cfg["task_type"],
                primary_metric          = cfg["primary_metric"],
                status                  = CompetitionStatus.ACTIVE,
                start_date              = now - timedelta(days=1),
                end_date                = now + timedelta(days=60),
                results_date            = now + timedelta(days=65),
                train_dataset_path      = train_rel,
                test_dataset_path       = truth_rel,
                created_by              = admin_user.id if admin_user else None,
                max_submissions_per_day = 20,
                max_submissions_total   = 200,
            )
            db.session.add(competition)
            db.session.flush()  # pour obtenir competition.id
            created += 1
            print(f"  Compétition évaluable '{cfg['slug']}' créée")

        # 3. Inscription du participant
        if participant and participant not in competition.participants:
            competition.participants.append(participant)

        # 4. Modèle .pkl + soumission (si pas déjà présente pour ce participant)
        if participant:
            existing_sub = Submission.query.filter_by(
                competition_id=competition.id, user_id=participant.id
            ).first()
            if not existing_sub:
                model_dir_rel = os.path.join(
                    "uploads", "submissions", str(competition.id), str(participant.id)
                )
                model_dir_abs = os.path.join(BASE_DIR, model_dir_rel)
                os.makedirs(model_dir_abs, exist_ok=True)

                model_filename = "seed_model.pkl"
                joblib.dump(model, os.path.join(model_dir_abs, model_filename))

                submission = Submission(
                    user_id        = participant.id,
                    competition_id = competition.id,
                    model_path     = os.path.join(model_dir_rel, model_filename),
                    model_type     = "sklearn",
                    status         = "pending",
                )
                db.session.add(submission)
                print(f"    + modèle .pkl + soumission (pending) pour '{cfg['slug']}'")
            else:
                print(f"    soumission déjà présente pour '{cfg['slug']}'")

    db.session.commit()
    print(f"\n Seed évaluation terminé : {created} compétition(s) évaluable(s) créée(s).")


# ──────────────────────────────────────────────────────────────
#  Fonction de seeding
# ──────────────────────────────────────────────────────────────

def seed():
    """Insère les données de seed dans la base (idempotent)."""
    created_users = 0
    created_competitions = 0

    # ── Utilisateurs ──────────────────────────────────────────
    admin_user = None
    for user_data in USERS:
        existing = User.query.filter_by(username=user_data["username"]).first()
        if existing:
            print(f"  Utilisateur '{user_data['username']}' existe déjà")
            if user_data["username"] == "admin-evalia":
                admin_user = existing
            continue

        user = User()
        user.name = user_data["name"]
        user.username = user_data["username"]
        user.email = user_data["email"]
        user.password = bcrypt.generate_password_hash(user_data["password"]).decode("utf-8")
        user.is_admin = user_data.get("is_admin", False)
        user.is_active = user_data.get("is_active", True)

        db.session.add(user)
        created_users += 1
        print(f"  Utilisateur '{user_data['username']}' créé")

        if user_data["username"] == "admin-evalia":
            admin_user = user

    db.session.flush()  # pour obtenir les IDs avant de créer les compétitions

    # ── Compétitions ──────────────────────────────────────────
    for comp_data in COMPETITIONS:
        existing = Competition.query.filter_by(slug=comp_data["slug"]).first()
        if existing:
            print(f"  Compétition '{comp_data['slug']}' existe déjà")
            continue

        competition = Competition(
            slug=comp_data["slug"],
            title=comp_data["title"],
            description=comp_data["description"],
            problem_statement=comp_data.get("problem_statement"),
            rules=comp_data.get("rules"),
            task_type=comp_data["task_type"],
            primary_metric=comp_data["primary_metric"],
            secondary_metrics=comp_data.get("secondary_metrics"),
            status=comp_data["status"],
            start_date=comp_data["start_date"],
            end_date=comp_data["end_date"],
            results_date=comp_data.get("results_date"),
            max_submissions_per_day=comp_data.get("max_submissions_per_day", 10),
            max_submissions_total=comp_data.get("max_submissions_total", 50),
            created_by=admin_user.id if admin_user else None,
        )
        db.session.add(competition)
        created_competitions += 1
        print(f"  Compétition '{comp_data['slug']}' créée")

    db.session.commit()

    print(f"\n Seed terminé : {created_users} utilisateur(s), {created_competitions} compétition(s) créé(s).")

    # ── Compétitions évaluables (dataset de test + modèle + soumission) ──
    participant = User.query.filter_by(username="stan-hto").first()
    seed_evaluation(admin_user, participant)


# ──────────────────────────────────────────────────────────────
#  Point d'entrée
# ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print(" Lancement du seed...")
    with app.app_context():
        seed()
