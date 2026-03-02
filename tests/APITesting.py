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
        os.environ['TESTING'] = 'test'
        self.client = app.test_client()

    @classmethod
    def tearDownClass(cls) -> None:
        os.environ.pop("TESTING")

    def test__recuperer_les_informations_d_un_user(self):
        response = self.client.get(
            "/api/auth/user-info/stan-hto",
            headers=self._base_header
        )
        if response.status_code != 200:
            logging.info(response.get_data(as_text=True))
        self.assertEqual(response.status_code, 200) # Ou bien assertIn

