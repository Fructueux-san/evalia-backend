"""
Les test d'API sont écrits dans ce fichier
en utilisant la librairie unittests
"""

import logging
from flask import json
from app import app
import unittest
import os 

class APITesting(unittest.TestCase):
    _token = ""
    _base_header = {'Content-type': 'application/json', 'accept': 'application/json'}

    def setUp(self) -> None:
        app.testing = True
        app.config['TESTING'] = True


    @classmethod
    def setUpClass(self):
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

