## Tests d'API — Evalia Backend

### Description
Les tests sont écrits avec `unittest` et utilisent le test client Flask (`app.test_client()`).
Ils sont **auto-suffisants** : chaque run crée ses propres données de test 
(utilisateurs avec UUID unique) et les nettoie automatiquement à la fin.

### Tests couverts (52 tests)

#### Auth — Inscription (`POST /api/auth/register`)
| # | Scénario | Attendu |
|---|----------|---------|
| 01 | Inscription valide | 201 + `id` |
| 02 | Username déjà pris | 409 |
| 03 | Email déjà utilisé | 409 |
| 04 | Champs requis manquants | 400 |
| 05 | Mot de passe trop court (< 6) | 400 |
| 06 | Email mal formé | 400 |
| 07 | Username trop court (< 3) | 400 |
| 08 | Content-Type non JSON | 415 |

#### Auth — Connexion (`POST /api/auth/login`)
| # | Scénario | Attendu |
|---|----------|---------|
| 09 | Login valide | 200 + `access_token` |
| 10 | Mauvais mot de passe | 401 |
| 11 | Utilisateur inexistant | 401 |
| 12 | Content-Type non JSON | 415 |
| 13 | Champs manquants | 400 |

#### Auth — Profil & infos
| # | Endpoint | Scénario | Attendu |
|---|----------|----------|---------|
| 14 | `GET /api/auth/user-info/<u>` | User existant | 200 |
| 15 | `GET /api/auth/user-info/<u>` | User inexistant | 404 |
| 16 | `GET /api/auth/me` | Sans JWT | 401 |
| 17 | `GET /api/auth/me` | JWT valide | 200 |
| 18 | `GET /api/auth/me` | Token invalide | 401/422 |
| 19 | `GET /api/auth/dashboard` | Sans JWT | 401 |
| 20 | `GET /api/auth/dashboard` | JWT valide | 200 |

#### Dashboard (`GET /api/dashboard/me`)
| # | Scénario | Attendu |
|---|----------|---------|
| 21 | Sans JWT | 401 |
| 22 | JWT valide | 200 |

#### Compétitions
| # | Endpoint | Scénario | Attendu |
|---|----------|----------|---------|
| 23 | `GET /api/competitions` | Liste publique | 200 |
| 24 | `GET /api/competitions?status=` | Statut invalide | 400 |
| 25 | `GET /api/competitions?task_type=` | Type invalide | 400 |
| 26 | `POST /api/competitions` | Sans JWT | 401 |
| 27 | `POST /api/competitions` | Création valide | 201 |
| 28 | `POST /api/competitions` | Données invalides | 400 |
| 29 | `POST /api/competitions` | Slug déjà pris | 409 |
| 30 | `POST /api/competitions` | end_date < start_date | 400 |
| 31 | `GET /api/competitions/<id>` | Détail existant | 200 |
| 32 | `GET /api/competitions/<id>` | UUID inexistant | 404 |
| 33 | `GET /api/competitions/<id>` | Identifiant non-UUID | 404 |
| 34 | `GET /api/competitions/my` | Sans JWT | 401 |
| 35 | `GET /api/competitions/my` | JWT valide | 200 |
| 36 | `POST /api/competitions/<id>/join` | Sans JWT | 401 |
| 37 | `POST /api/competitions/<id>/join` | Compétition DRAFT | 403 |
| 38 | `POST /api/competitions/<id>/join` | Compétition inexistante | 404 |
| 39 | `DELETE /api/competitions/<id>/leave` | Non inscrit | 404 |
| 40 | `GET /api/competitions/<id>/participants` | Liste | 200 |
| 41 | `PATCH /api/competitions/<id>/status` | Sans JWT | 401 |
| 42 | `PATCH /api/competitions/<id>/status` | Non admin | 403 |
| 43 | `GET /api/competitions/<id>/raw-dataset` | Fichier absent | 404 |
| 44 | `GET /api/competitions/<id>/processed-dataset` | Non admin | 403 |

#### Évaluation
| # | Endpoint | Scénario | Attendu |
|---|----------|----------|---------|
| 45 | `GET /api/eval/all-type` | Types disponibles | 200 |
| 46 | `POST /api/eval/<id>/submit` | Sans JWT | 401 |
| 47 | `POST /api/eval/<id>/submit` | Sans fichier modèle | 400 |
| 48 | `GET /api/eval/status/<id>` | Sans JWT | 401 |
| 49 | `GET /api/eval/status/<id>` | Soumission inexistante | 404 |
| 50 | `GET /api/eval/<id>/submissions` | Sans JWT | 401 |
| 51 | `GET /api/eval/<id>/submissions` | Compétition existante | 200 |
| 52 | `GET /api/eval/<id>/submissions` | Compétition inexistante | 404 |

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
