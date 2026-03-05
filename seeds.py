"""
Seeds — Peupler la base de données avec des données initiales.

Script idempotent : vérifie si les données existent avant d'insérer.
Usage :
    python3 seeds.py
"""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

from app import app
from confs.main import db, bcrypt
from models.user import User
from models.competition import Competition, CompetitionStatus, TaskType, MetricName


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


# ──────────────────────────────────────────────────────────────
#  Point d'entrée
# ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print(" Lancement du seed...")
    with app.app_context():
        seed()
