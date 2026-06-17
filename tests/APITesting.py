"""
Tests d'API — tests auto-suffisants avec unittest.

Chaque exécution crée ses propres données (utilisateurs / compétitions avec un
identifiant unique) et les nettoie automatiquement à la fin (tearDownClass).
Aucune donnée préexistante (seed) n'est nécessaire pour que la suite passe.

Les tests sont nommés `test_NN_...` afin d'être exécutés dans un ordre
déterministe : les données partagées (token JWT, compétition créée, ...) sont
préparées dans `setUpClass` puis réutilisées par les tests dépendants.

Exécution :
    python3 -m pytest -v tests/APITesting.py -o cache_dir=/tmp

    # Depuis le conteneur Docker :
    docker exec -it backend-evalia python3 -m pytest -v tests/APITesting.py -o cache_dir=/tmp
"""

import logging
import os
import unittest
import uuid
from datetime import datetime, timedelta

from app import app
from confs.main import db



#  Helpers — génération de données uniques à chaque exécution

def _unique_suffix() -> str:
    """Retourne un suffixe court et unique pour éviter les collisions."""
    return uuid.uuid4().hex[:8]


def make_user_payload(prefix: str = "user") -> dict:
    """Construit un payload d'inscription valide et unique."""
    suffix = _unique_suffix()
    return {
        "username": f"{prefix}_{suffix}",
        "email":    f"{prefix}_{suffix}@evalia-test.local",
        "password": "TestPass123!",
        "name":     "Test User",
    }


def make_competition_form(prefix: str = "comp") -> dict:
    """Construit un formulaire de création de compétition valide et unique."""
    suffix = _unique_suffix()
    start = datetime.utcnow() + timedelta(days=2)
    end   = datetime.utcnow() + timedelta(days=30)
    return {
        "slug":           f"{prefix}-{suffix}",
        "title":          f"Compétition de test {suffix}",
        "description":    "Description suffisamment longue pour la validation.",
        "task_type":      "regression",
        "primary_metric": "rmse",
        "start_date":     start.isoformat(),
        "end_date":       end.isoformat(),
    }


class APITesting(unittest.TestCase):
    """Tests d'API auto-suffisants pour le backend Evalia."""

    # ── État partagé entre les tests ───────────────────────────
    _token = ""
    _user_id = ""
    _username = ""
    _competition_id = ""

    _base_header = {
        "Content-Type": "application/json",
        "Accept":       "application/json",
    }

    _created_user_ids = []
    _created_competition_ids = []


    #  Setup / Teardown


    @classmethod
    def setUpClass(cls):
        """Prépare l'environnement et un utilisateur de référence + son token JWT."""
        app.testing = True
        app.config["TESTING"] = True
        # On veut récupérer les réponses HTTP (500, etc.), pas des exceptions.
        app.config["PROPAGATE_EXCEPTIONS"] = False
        app.config["TRAP_HTTP_EXCEPTIONS"] = False
        os.environ["TESTING"] = "test"

        cls.client = app.test_client()
        cls._created_user_ids = []
        cls._created_competition_ids = []

        # S'assurer que les tables existent
        with app.app_context():
            db.create_all()

        # ── Utilisateur de référence (pour les tests nécessitant un JWT) ──
        cls._reference_user = make_user_payload("reference")

        reg = cls.client.post(
            "/api/auth/register",
            json=cls._reference_user,
            headers=cls._base_header,
        )
        if reg.status_code == 201:
            cls._user_id = reg.get_json().get("id", "")
            cls._created_user_ids.append(cls._user_id)
        cls._username = cls._reference_user["username"]

        login = cls.client.post(
            "/api/auth/login",
            json={
                "username": cls._reference_user["username"],
                "password": cls._reference_user["password"],
            },
            headers=cls._base_header,
        )
        if login.status_code == 200:
            cls._token = login.get_json().get("access_token", "")

    @classmethod
    def tearDownClass(cls):
        """Supprime toutes les données créées pendant la suite de tests."""
        os.environ.pop("TESTING", None)

        with app.app_context():
            from models.user import User
            from models.competition import Competition
            from models.submission import Submission

            # 1. Supprimer les soumissions liées aux compétitions de test
            for cid in cls._created_competition_ids:
                for sub in Submission.query.filter_by(competition_id=cid).all():
                    db.session.delete(sub)

            # 2. Supprimer les compétitions de test
            for cid in cls._created_competition_ids:
                comp = db.session.get(Competition, cid)
                if comp:
                    db.session.delete(comp)

            # 3. Supprimer les utilisateurs de test
            for uid in cls._created_user_ids:
                user = db.session.get(User, uid)
                if user:
                    db.session.delete(user)

            db.session.commit()

    def setUp(self):
        app.testing = True
        app.config["TESTING"] = True
        os.environ["TESTING"] = "test"
        self.client = app.test_client()

    # ── Helpers d'instance ─────────────────────────────────────

    def _auth_header(self, token: str = None) -> dict:
        """Retourne un en-tête JSON incluant le Bearer token."""
        return {
            **self._base_header,
            "Authorization": f"Bearer {token or self._token}",
        }


    #  1. AUTH — POST /api/auth/register


    def test_01_register_success(self):
        """Inscription valide → 201 + id retourné."""
        payload = make_user_payload("register_ok")
        response = self.client.post(
            "/api/auth/register", json=payload, headers=self._base_header
        )
        if response.status_code != 201:
            logging.info(response.get_data(as_text=True))
        self.assertEqual(response.status_code, 201)

        body = response.get_json()
        self.assertIn("id", body)
        type(self)._created_user_ids.append(body["id"])

    def test_02_register_duplicate_username(self):
        """Username déjà pris → 409."""
        payload = make_user_payload("dup_username")
        first = self.client.post(
            "/api/auth/register", json=payload, headers=self._base_header
        )
        self.assertEqual(first.status_code, 201)
        type(self)._created_user_ids.append(first.get_json()["id"])

        # Même username, email différent
        payload_2 = dict(payload)
        payload_2["email"] = f"other_{_unique_suffix()}@evalia-test.local"
        response = self.client.post(
            "/api/auth/register", json=payload_2, headers=self._base_header
        )
        self.assertEqual(response.status_code, 409)

    def test_03_register_duplicate_email(self):
        """Email déjà utilisé → 409."""
        payload = make_user_payload("dup_email")
        first = self.client.post(
            "/api/auth/register", json=payload, headers=self._base_header
        )
        self.assertEqual(first.status_code, 201)
        type(self)._created_user_ids.append(first.get_json()["id"])

        # Même email, username différent
        payload_2 = dict(payload)
        payload_2["username"] = f"other_{_unique_suffix()}"
        response = self.client.post(
            "/api/auth/register", json=payload_2, headers=self._base_header
        )
        self.assertEqual(response.status_code, 409)

    def test_04_register_missing_fields(self):
        """Champs requis manquants → 400."""
        response = self.client.post(
            "/api/auth/register",
            json={"username": f"incomplete_{_unique_suffix()}"},
            headers=self._base_header,
        )
        self.assertEqual(response.status_code, 400)

    def test_05_register_password_too_short(self):
        """Mot de passe trop court (< 6 caractères) → 400."""
        payload = make_user_payload("short_pwd")
        payload["password"] = "123"
        response = self.client.post(
            "/api/auth/register", json=payload, headers=self._base_header
        )
        self.assertEqual(response.status_code, 400)

    def test_06_register_invalid_email(self):
        """Email mal formé → 400."""
        payload = make_user_payload("bad_email")
        payload["email"] = "ceci-nest-pas-un-email"
        response = self.client.post(
            "/api/auth/register", json=payload, headers=self._base_header
        )
        self.assertEqual(response.status_code, 400)

    def test_07_register_username_too_short(self):
        """Username trop court (< 3 caractères) → 400."""
        payload = make_user_payload("short_username")
        payload["username"] = "ab"
        response = self.client.post(
            "/api/auth/register", json=payload, headers=self._base_header
        )
        self.assertEqual(response.status_code, 400)

    def test_08_register_wrong_content_type(self):
        """Content-Type non JSON → 415."""
        response = self.client.post(
            "/api/auth/register",
            data="username=foo",
            content_type="text/plain",
        )
        self.assertEqual(response.status_code, 415)


    #  2. AUTH — POST /api/auth/login


    def test_09_login_success(self):
        """Login valide → 200 + access_token + infos utilisateur."""
        response = self.client.post(
            "/api/auth/login",
            json={
                "username": self._reference_user["username"],
                "password": self._reference_user["password"],
            },
            headers=self._base_header,
        )
        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertIn("access_token", body)
        self.assertTrue(body["access_token"])
        self.assertEqual(body["user"]["username"], self._reference_user["username"])

    def test_10_login_wrong_password(self):
        """Mot de passe incorrect → 401."""
        response = self.client.post(
            "/api/auth/login",
            json={
                "username": self._reference_user["username"],
                "password": "MauvaisMotDePasse!",
            },
            headers=self._base_header,
        )
        self.assertEqual(response.status_code, 401)

    def test_11_login_nonexistent_user(self):
        """Utilisateur inexistant → 401."""
        response = self.client.post(
            "/api/auth/login",
            json={"username": f"ghost_{_unique_suffix()}", "password": "whatever123"},
            headers=self._base_header,
        )
        self.assertEqual(response.status_code, 401)

    def test_12_login_wrong_content_type(self):
        """Content-Type non JSON → 415."""
        response = self.client.post(
            "/api/auth/login",
            data="username=foo&password=bar",
            content_type="application/x-www-form-urlencoded",
        )
        self.assertEqual(response.status_code, 415)

    def test_13_login_missing_fields(self):
        """Champs requis manquants → 400."""
        response = self.client.post(
            "/api/auth/login",
            json={"username": self._reference_user["username"]},
            headers=self._base_header,
        )
        self.assertEqual(response.status_code, 400)


    #  3. AUTH — GET /api/auth/user-info/<username>


    def test_14_user_info_existing(self):
        """Informations publiques d'un utilisateur existant → 200."""
        response = self.client.get(
            f"/api/auth/user-info/{self._username}",
            headers=self._base_header,
        )
        if response.status_code != 200:
            logging.info(response.get_data(as_text=True))
        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertEqual(body["username"], self._username)

    def test_15_user_info_nonexistent(self):
        """Utilisateur inexistant → 404."""
        response = self.client.get(
            f"/api/auth/user-info/ghost_{_unique_suffix()}",
            headers=self._base_header,
        )
        self.assertEqual(response.status_code, 404)


    #  4. AUTH — GET /api/auth/me


    def test_16_me_without_jwt(self):
        """Accès au profil sans token → 401."""
        response = self.client.get("/api/auth/me", headers=self._base_header)
        self.assertEqual(response.status_code, 401)

    def test_17_me_with_valid_jwt(self):
        """Accès au profil avec un token valide → 200."""
        response = self.client.get("/api/auth/me", headers=self._auth_header())
        if response.status_code != 200:
            logging.info(response.get_data(as_text=True))
        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertEqual(body["username"], self._username)

    def test_18_me_with_invalid_token(self):
        """Token malformé → 401 ou 422 (selon flask-jwt-extended)."""
        response = self.client.get(
            "/api/auth/me",
            headers={**self._base_header, "Authorization": "Bearer not.a.valid.token"},
        )
        self.assertIn(response.status_code, (401, 422))


    #  5. AUTH — GET /api/auth/dashboard


    def test_19_auth_dashboard_without_jwt(self):
        """Dashboard (auth) sans token → 401."""
        response = self.client.get("/api/auth/dashboard", headers=self._base_header)
        self.assertEqual(response.status_code, 401)

    def test_20_auth_dashboard_with_jwt(self):
        """Dashboard (auth) avec token → 200 + structure attendue."""
        response = self.client.get("/api/auth/dashboard", headers=self._auth_header())
        if response.status_code != 200:
            logging.info(response.get_data(as_text=True))
        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertIn("user", body)
        self.assertIn("stats", body)


    #  6. DASHBOARD — GET /api/dashboard/me


    def test_21_dashboard_me_without_jwt(self):
        """Dashboard agrégé sans token → 401."""
        response = self.client.get("/api/dashboard/me", headers=self._base_header)
        self.assertEqual(response.status_code, 401)

    def test_22_dashboard_me_with_jwt(self):
        """Dashboard agrégé avec token → 200 + structure attendue."""
        response = self.client.get("/api/dashboard/me", headers=self._auth_header())
        if response.status_code != 200:
            logging.info(response.get_data(as_text=True))
        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertIn("user", body)
        self.assertIn("competitions", body)
        self.assertIn("stats", body)


    #  7. COMPÉTITIONS — listing & création


    def test_23_list_competitions(self):
        """Liste publique des compétitions → 200 + pagination."""
        response = self.client.get("/api/competitions", headers=self._base_header)
        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertIn("competitions", body)
        self.assertIn("pagination", body)

    def test_24_list_competitions_invalid_status(self):
        """Filtre de statut invalide → 400."""
        response = self.client.get(
            "/api/competitions?status=statut_bidon", headers=self._base_header
        )
        self.assertEqual(response.status_code, 400)

    def test_25_list_competitions_invalid_task_type(self):
        """Filtre de type de tâche invalide → 400."""
        response = self.client.get(
            "/api/competitions?task_type=tache_bidon", headers=self._base_header
        )
        self.assertEqual(response.status_code, 400)

    def test_26_create_competition_without_jwt(self):
        """Création sans token → 401."""
        response = self.client.post(
            "/api/competitions", data=make_competition_form()
        )
        self.assertEqual(response.status_code, 401)

    def test_27_create_competition_success(self):
        """Création valide avec token → 201 + id/slug."""
        form = make_competition_form("created")
        response = self.client.post(
            "/api/competitions",
            data=form,
            headers={"Authorization": f"Bearer {self._token}"},
            content_type="multipart/form-data",
        )
        if response.status_code != 201:
            logging.info(response.get_data(as_text=True))
        self.assertEqual(response.status_code, 201)
        body = response.get_json()
        self.assertIn("id", body)
        self.assertEqual(body["slug"], form["slug"])

        # Mémorisé pour les tests suivants et le nettoyage
        type(self)._competition_id = body["id"]
        type(self)._created_competition_ids.append(body["id"])

    def test_28_create_competition_invalid_data(self):
        """Données invalides (champs manquants) → 400."""
        response = self.client.post(
            "/api/competitions",
            data={"title": "x"},  # slug, description, dates manquants + titre trop court
            headers={"Authorization": f"Bearer {self._token}"},
            content_type="multipart/form-data",
        )
        self.assertEqual(response.status_code, 400)

    def test_29_create_competition_duplicate_slug(self):
        """Slug déjà pris → 409."""
        form = make_competition_form("dup_slug")
        first = self.client.post(
            "/api/competitions",
            data=form,
            headers={"Authorization": f"Bearer {self._token}"},
            content_type="multipart/form-data",
        )
        self.assertEqual(first.status_code, 201)
        type(self)._created_competition_ids.append(first.get_json()["id"])

        # Réutilisation du même slug
        form_2 = make_competition_form("dup_slug_2")
        form_2["slug"] = form["slug"]
        response = self.client.post(
            "/api/competitions",
            data=form_2,
            headers={"Authorization": f"Bearer {self._token}"},
            content_type="multipart/form-data",
        )
        self.assertEqual(response.status_code, 409)

    def test_30_create_competition_end_before_start(self):
        """Date de clôture antérieure à la date de début → 400."""
        form = make_competition_form("bad_dates")
        form["start_date"] = (datetime.utcnow() + timedelta(days=30)).isoformat()
        form["end_date"]   = (datetime.utcnow() + timedelta(days=10)).isoformat()
        response = self.client.post(
            "/api/competitions",
            data=form,
            headers={"Authorization": f"Bearer {self._token}"},
            content_type="multipart/form-data",
        )
        self.assertEqual(response.status_code, 400)


    #  8. COMPÉTITIONS — détail, participations, statut


    def test_31_get_competition_by_id(self):
        """Détail d'une compétition existante → 200."""
        self.assertTrue(self._competition_id, "Compétition de référence non créée")
        response = self.client.get(
            f"/api/competitions/{self._competition_id}", headers=self._base_header
        )
        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertEqual(body["id"], self._competition_id)

    def test_32_get_competition_nonexistent(self):
        """Compétition inexistante (UUID valide) → 404."""
        response = self.client.get(
            f"/api/competitions/{uuid.uuid4()}", headers=self._base_header
        )
        self.assertEqual(response.status_code, 404)

    def test_33_get_competition_invalid_uuid(self):
        """Identifiant non-UUID → 404 (route non matchée)."""
        response = self.client.get(
            "/api/competitions/pas-un-uuid", headers=self._base_header
        )
        self.assertEqual(response.status_code, 404)

    def test_34_my_competitions_without_jwt(self):
        """Mes compétitions sans token → 401."""
        response = self.client.get("/api/competitions/my", headers=self._base_header)
        self.assertEqual(response.status_code, 401)

    def test_35_my_competitions_with_jwt(self):
        """Mes compétitions avec token → 200."""
        response = self.client.get(
            "/api/competitions/my", headers=self._auth_header()
        )
        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertIn("competitions", body)

    def test_36_join_competition_without_jwt(self):
        """Rejoindre une compétition sans token → 401."""
        self.assertTrue(self._competition_id)
        response = self.client.post(
            f"/api/competitions/{self._competition_id}/join", headers=self._base_header
        )
        self.assertEqual(response.status_code, 401)

    def test_37_join_draft_competition_forbidden(self):
        """Rejoindre une compétition en DRAFT → 403 (inscriptions fermées)."""
        self.assertTrue(self._competition_id)
        response = self.client.post(
            f"/api/competitions/{self._competition_id}/join",
            headers=self._auth_header(),
        )
        self.assertEqual(response.status_code, 403)

    def test_38_join_nonexistent_competition(self):
        """Rejoindre une compétition inexistante → 404."""
        response = self.client.post(
            f"/api/competitions/{uuid.uuid4()}/join", headers=self._auth_header()
        )
        self.assertEqual(response.status_code, 404)

    def test_39_leave_competition_not_joined(self):
        """Quitter une compétition à laquelle on n'est pas inscrit → 404."""
        self.assertTrue(self._competition_id)
        response = self.client.delete(
            f"/api/competitions/{self._competition_id}/leave",
            headers=self._auth_header(),
        )
        self.assertEqual(response.status_code, 404)

    def test_40_get_participants(self):
        """Liste des participants d'une compétition → 200."""
        self.assertTrue(self._competition_id)
        response = self.client.get(
            f"/api/competitions/{self._competition_id}/participants",
            headers=self._base_header,
        )
        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertIn("participants", body)
        self.assertIn("count", body)

    def test_41_update_status_without_jwt(self):
        """Changer le statut sans token → 401."""
        self.assertTrue(self._competition_id)
        response = self.client.patch(
            f"/api/competitions/{self._competition_id}/status",
            json={"status": "active"},
            headers=self._base_header,
        )
        self.assertEqual(response.status_code, 401)

    def test_42_update_status_not_admin(self):
        """Changer le statut sans droits admin → 403."""
        self.assertTrue(self._competition_id)
        response = self.client.patch(
            f"/api/competitions/{self._competition_id}/status",
            json={"status": "active"},
            headers=self._auth_header(),
        )
        self.assertEqual(response.status_code, 403)

    def test_43_raw_dataset_not_found(self):
        """Dataset brut inexistant pour la compétition → 404."""
        self.assertTrue(self._competition_id)
        response = self.client.get(
            f"/api/competitions/{self._competition_id}/raw-dataset",
            headers=self._base_header,
        )
        self.assertEqual(response.status_code, 404)

    def test_44_processed_dataset_requires_admin(self):
        """Dataset traité réservé aux admins → 403 sans droits admin."""
        self.assertTrue(self._competition_id)
        response = self.client.get(
            f"/api/competitions/{self._competition_id}/processed-dataset",
            headers=self._auth_header(),
        )
        self.assertEqual(response.status_code, 403)


    #  9. ÉVALUATION — types, soumission, statut


    def test_45_eval_all_types(self):
        """Types d'évaluation disponibles → 200 + mapping non vide."""
        response = self.client.get("/api/eval/all-type", headers=self._base_header)
        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertIsInstance(body, dict)
        self.assertIn("sklearn", body)

    def test_46_submit_without_jwt(self):
        """Soumettre un modèle sans token → 401."""
        self.assertTrue(self._competition_id)
        response = self.client.post(
            f"/api/eval/{self._competition_id}/submit",
            data={"model_type": "sklearn"},
            content_type="multipart/form-data",
        )
        self.assertEqual(response.status_code, 401)

    def test_47_submit_without_file(self):
        """Soumettre sans fichier de modèle → 400."""
        self.assertTrue(self._competition_id)
        response = self.client.post(
            f"/api/eval/{self._competition_id}/submit",
            data={"model_type": "sklearn"},
            headers={"Authorization": f"Bearer {self._token}"},
            content_type="multipart/form-data",
        )
        self.assertEqual(response.status_code, 400)

    def test_48_submission_status_without_jwt(self):
        """Consulter le statut d'une soumission sans token → 401."""
        response = self.client.get(
            f"/api/eval/status/{uuid.uuid4()}", headers=self._base_header
        )
        self.assertEqual(response.status_code, 401)

    def test_49_submission_status_nonexistent(self):
        """Statut d'une soumission inexistante → 404."""
        response = self.client.get(
            f"/api/eval/status/{uuid.uuid4()}", headers=self._auth_header()
        )
        self.assertEqual(response.status_code, 404)

    def test_50_my_submissions_without_jwt(self):
        """Lister ses soumissions sans token → 401."""
        self.assertTrue(self._competition_id)
        response = self.client.get(
            f"/api/eval/{self._competition_id}/submissions", headers=self._base_header
        )
        self.assertEqual(response.status_code, 401)

    def test_51_my_submissions_with_jwt(self):
        """Lister ses soumissions pour une compétition existante → 200."""
        self.assertTrue(self._competition_id)
        response = self.client.get(
            f"/api/eval/{self._competition_id}/submissions",
            headers=self._auth_header(),
        )
        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertIn("submissions", body)
        self.assertIn("count", body)

    def test_52_my_submissions_nonexistent_competition(self):
        """Lister ses soumissions pour une compétition inexistante → 404."""
        response = self.client.get(
            f"/api/eval/{uuid.uuid4()}/submissions", headers=self._auth_header()
        )
        self.assertEqual(response.status_code, 404)


if __name__ == "__main__":
    unittest.main(verbosity=2)
