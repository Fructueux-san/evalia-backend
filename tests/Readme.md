## Tests d'API — Evalia Backend

### Description
Les tests sont écrits avec `unittest` et utilisent le test client Flask (`app.test_client()`).
Ils sont **auto-suffisants** : chaque run crée ses propres données de test 
(utilisateurs avec UUID unique) et les nettoie automatiquement à la fin.

### Tests couverts (18 tests)

| # | Endpoint | Scénario |
|---|----------|----------|
| 01 | `POST /api/auth/register` | Inscription réussie → 201 |
| 02 | `POST /api/auth/register` | Username déjà pris → 409 |
| 03 | `POST /api/auth/register` | Email déjà utilisé → 409 |
| 04 | `POST /api/auth/register` | Champs manquants → 400 |
| 05 | `POST /api/auth/register` | Mot de passe trop court → 400 |
| 06 | `POST /api/auth/login` | Login valide → 200 + token |
| 07 | `POST /api/auth/login` | Mauvais mot de passe → 401 |
| 08 | `POST /api/auth/login` | User inexistant → 401 |
| 09 | `POST /api/auth/login` | Content-Type invalide → 415 |
| 10 | `GET /api/auth/user-info/<u>` | User existant → 200 |
| 11 | `GET /api/auth/user-info/<u>` | User inexistant → 404 |
| 12 | `GET /api/auth/me` | Sans JWT → 401 |
| 13 | `GET /api/auth/me` | Avec JWT valide → 200 |
| 14 | `GET /api/auth/me` | Token invalide → 401/422 |
| 15 | `GET /api/competitions` | Liste compétitions → 200 |
| 16 | `GET /api/eval/all-type` | Types d'évaluation → 200 |
| 17 | `POST /api/auth/register` | 2ème utilisateur → 201 |
| 18 | `GET /api/auth/user-info/<u>` | 2ème user → 200 |

### Lancer les tests manuellement

```bash
# Depuis le conteneur Docker :
docker exec -it backend-evalia python3 -m pytest -v tests/APITesting.py -o cache_dir=/tmp

# Ou localement (si les variables d'env et la DB sont configurées) :
python3 -m pytest -v tests/APITesting.py
```

### Comportement dans init.sh
Les tests sont lancés **avant** le serveur Flask/gunicorn.
Le serveur ne démarre que si **tous les tests passent** (`&&`).
Cela garantit que l'API est fonctionnelle avant d'accepter du trafic.

### Données de test
- Le CSV `homeprices.csv` et le fichier `model_pickle` sont des artefacts pour tester
  les compétitions (upload de données brutes/traitées).
