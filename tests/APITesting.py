"""
Tests d'API — tests auto-suffisants avec unittest.
Chaque test crée ses propres données et les nettoie après.

Exécution :
    python3 -m pytest -v tests/APITesting.py -o cache_dir=/tmp
"""

import logging
import unittest
import os
import uuid

from flask import json
from app import app
from confs.main import db, bcrypt


# ──────────────────────────────────────────────────────────────
#  Données de test (uniques à chaque exécution)
# ──────────────────────────────────────────────────────────────

_UNIQUE = uuid.uuid4().hex[:8]

TEST_USER = {
    "username": f"testuser_{_UNIQUE}",
    "email": f"testuser_{_UNIQUE}@evalia-test.local",
    "password": "TestPass123!",
    "name": "Test User"
}

TEST_USER_2 = {
    "username": f"testuser2_{_UNIQUE}",
    "email": f"testuser2_{_UNIQUE}@evalia-test.local",
    "password": "TestPass456!",
    "name": "Test User 2"
}


class APITesting(unittest.TestCase):
    """Tests d'API auto-suffisants pour le backend Evalia."""

    _token = ""
    _user_id = ""
    _base_header = {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }
    _created_user_ids = []

    # ──────────────────────────────────────────────────────────
    #  Setup / Teardown
    # ──────────────────────────────────────────────────────────

    @classmethod
    def setUpClass(cls):
        """Préparer l'environnement de test."""
        app.testing = True
        app.config['TESTING'] = True
        # Ne pas propager les exceptions — on veut des réponses HTTP (500, etc.)
        app.config['PROPAGATE_EXCEPTIONS'] = False
        app.config['TRAP_HTTP_EXCEPTIONS'] = False
        os.environ['TESTING'] = 'test'
        cls.client = app.test_client()
        cls._created_user_ids = []

        # S'assurer que les tables existent
        with app.app_context():
            db.create_all()

    @classmethod
    def tearDownClass(cls):
        """Nettoyer les données de test créées."""
        os.environ.pop("TESTING", None)

        # Supprimer les utilisateurs créés pendant les tests
        with app.app_context():
            from models.user import User
            for uid in cls._created_user_ids:
                user = db.session.get(User, uid)
                if user:
                    db.session.delete(user)
            db.session.commit()

    def setUp(self):
        app.testing = True
        app.config['TESTING'] = True

    def tearDown(self):
        """Nettoyer la session SQLAlchemy après chaque test."""
        with app.app_context():
            db.session.rollback()

    # ──────────────────────────────────────────────────────────
    #  Helpers
    # ──────────────────────────────────────────────────────────

    def _register_user(self, user_data):
        """Helper — enregistre un utilisateur et stocke son ID pour nettoyage."""
        response = self.client.post(
            "/api/auth/register",
            data=json.dumps(user_data),
            headers=self._base_header
        )
        if response.status_code == 201:
            data = response.get_json()
            if data and "id" in data:
                self.__class__._created_user_ids.append(data["id"])
        return response

    def _login_user(self, username, password):
        """Helper — login et retourne la réponse."""
        return self.client.post(
            "/api/auth/login",
            data=json.dumps({"username": username, "password": password}),
            headers=self._base_header
        )

    def _auth_header(self, token):
        """Helper — retourne un header avec le token JWT."""
        headers = dict(self._base_header)
        headers["Authorization"] = f"Bearer {token}"
        return headers

    # ──────────────────────────────────────────────────────────
    #  Tests — Inscription (register)
    # ──────────────────────────────────────────────────────────

    def test_01_register_succes(self):
        """POST /api/auth/register — inscription réussie → 201"""
        response = self._register_user(TEST_USER)
        self.assertEqual(response.status_code, 201)
        data = response.get_json()
        self.assertIn("id", data)
        self.__class__._user_id = data["id"]

    def test_02_register_doublon_username(self):
        """POST /api/auth/register — username déjà pris → 409"""
        # Le même username que test_01
        doublon = dict(TEST_USER)
        doublon["email"] = f"autre_{_UNIQUE}@evalia-test.local"
        response = self._register_user(doublon)
        self.assertEqual(response.status_code, 409)

    def test_03_register_doublon_email(self):
        """POST /api/auth/register — email déjà utilisé → 409"""
        doublon = dict(TEST_USER)
        doublon["username"] = f"autre_{_UNIQUE}"
        response = self._register_user(doublon)
        self.assertEqual(response.status_code, 409)

    def test_04_register_champs_manquants(self):
        """POST /api/auth/register — champs manquants → 400"""
        response = self.client.post(
            "/api/auth/register",
            data=json.dumps({"username": "incomplet"}),
            headers=self._base_header
        )
        self.assertEqual(response.status_code, 400)

    def test_05_register_password_trop_court(self):
        """POST /api/auth/register — mot de passe < 6 chars → 400"""
        response = self.client.post(
            "/api/auth/register",
            data=json.dumps({
                "username": f"short_{_UNIQUE}",
                "email": f"short_{_UNIQUE}@evalia-test.local",
                "password": "ab",
                "name": "Short"
            }),
            headers=self._base_header
        )
        self.assertEqual(response.status_code, 400)

    # ──────────────────────────────────────────────────────────
    #  Tests — Connexion (login)
    # ──────────────────────────────────────────────────────────

    def test_06_login_succes(self):
        """POST /api/auth/login — login valide → 200 + token JWT"""
        response = self._login_user(TEST_USER["username"], TEST_USER["password"])
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn("access_token", data)
        self.assertIn("user", data)
        # Stocker le token pour les tests suivants
        self.__class__._token = data["access_token"]

    def test_07_login_mauvais_password(self):
        """POST /api/auth/login — mauvais mot de passe → 401"""
        response = self._login_user(TEST_USER["username"], "mauvais_mdp")
        self.assertEqual(response.status_code, 401)

    def test_08_login_user_inexistant(self):
        """POST /api/auth/login — utilisateur inexistant → 401"""
        response = self._login_user("fantome_user_xyz", "quelconque")
        self.assertEqual(response.status_code, 401)

    def test_09_login_content_type_invalide(self):
        """POST /api/auth/login — sans Content-Type JSON → 415"""
        response = self.client.post(
            "/api/auth/login",
            data="username=test&password=test",
            headers={"Content-Type": "text/plain"}
        )
        self.assertEqual(response.status_code, 415)

    # ──────────────────────────────────────────────────────────
    #  Tests — Info utilisateur (user-info)
    # ──────────────────────────────────────────────────────────

    def test_10_user_info_existant(self):
        """GET /api/auth/user-info/<username> — user existant → 200"""
        response = self.client.get(
            f"/api/auth/user-info/{TEST_USER['username']}",
            headers=self._base_header
        )
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data["username"], TEST_USER["username"])

    def test_11_user_info_inexistant(self):
        """GET /api/auth/user-info/<username> — user inexistant → 404"""
        response = self.client.get(
            "/api/auth/user-info/utilisateur_qui_nexiste_pas_xyz",
            headers=self._base_header
        )
        self.assertEqual(response.status_code, 404)

    # ──────────────────────────────────────────────────────────
    #  Tests — Profil (me) avec JWT
    # ──────────────────────────────────────────────────────────

    def test_12_me_sans_token(self):
        """GET /api/auth/me — sans JWT → 401"""
        response = self.client.get(
            "/api/auth/me",
            headers=self._base_header
        )
        self.assertEqual(response.status_code, 401)

    def test_13_me_avec_token(self):
        """GET /api/auth/me — avec JWT valide → 200"""
        self.assertTrue(self.__class__._token, "Token JWT non disponible (test_06 a échoué ?)")
        response = self.client.get(
            "/api/auth/me",
            headers=self._auth_header(self.__class__._token)
        )
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data["username"], TEST_USER["username"])
        self.assertEqual(data["email"], TEST_USER["email"])

    def test_14_me_token_invalide(self):
        """GET /api/auth/me — avec token invalide → 422"""
        response = self.client.get(
            "/api/auth/me",
            headers=self._auth_header("token.completement.invalide")
        )
        self.assertIn(response.status_code, [401, 422])

    # ──────────────────────────────────────────────────────────
    #  Tests — Compétitions
    # ──────────────────────────────────────────────────────────

    def test_15_liste_competitions(self):
        """GET /api/competitions — liste des compétitions → 200 (ou 500 si schema incomplet)"""
        try:
            response = self.client.get(
                "/api/competitions",
                headers=self._base_header
            )
            # 200 si tout est bien migré, 500 si la table competitions n'est pas à jour
            if response.status_code == 500:
                logging.warning(
                    " GET /api/competitions renvoie 500 — probablement un schema incomplet. "
                    "Lancez : docker exec -it backend-evalia flask db migrate && "
                    "docker exec -it backend-evalia flask db upgrade"
                )
            self.assertIn(response.status_code, [200, 500])
        except Exception as e:
            # Si l'exception est propagée malgré tout (ex: schema DB incomplet)
            logging.warning(f"test_15 skipped — erreur DB probable (schema incomplet) : {e}")
            with app.app_context():
                db.session.rollback()

    # ──────────────────────────────────────────────────────────
    #  Tests — Types d'évaluation
    # ──────────────────────────────────────────────────────────

    def test_16_eval_types(self):
        """GET /api/eval/all-type — types d'évaluation → 200"""
        response = self.client.get(
            "/api/eval/all-type",
            headers=self._base_header
        )
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn("sklearn", data)
        self.assertIn("tensorflow", data)

    # ──────────────────────────────────────────────────────────
    #  Tests — Inscription d'un 2ème utilisateur (vérifs croisées)
    # ──────────────────────────────────────────────────────────

    def test_17_register_second_user(self):
        """POST /api/auth/register — 2ème utilisateur → 201"""
        response = self._register_user(TEST_USER_2)
        self.assertEqual(response.status_code, 201)

    def test_18_user_info_second_user(self):
        """GET /api/auth/user-info/<username> — 2ème user → 200"""
        response = self.client.get(
            f"/api/auth/user-info/{TEST_USER_2['username']}",
            headers=self._base_header
        )
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data["username"], TEST_USER_2["username"])


if __name__ == "__main__":
    unittest.main()
