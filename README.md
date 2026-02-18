# evalia-backend

Backend de la plateforme de suivi et d'évaluation des modèles d'IA
dans un contexte de compétition 

## Technologies 
API écrit en Python (Flask), avec un peu de docker (via compose), 
une DB Postgresql et du scripting bash



### Les migration

```bash
flask db init
flask db migrate

```

## Pour lancer le projet 

1. **En production**
```bash
docker compose up -d 

```
2. **En dev**
```bash
docker compose -f docker-compose.dev.yaml -d 
```

## Pour voir les logs des containers
```bash
docker logs <nom-du-conteneur> -f [-n 100]
```

**Exemple concret**
```bash
docker logs backend-evalia -f 
```
CTRL + C pour couper. 


## Arrêter tout l'infra (backend + db)
```bash
docker compose down 
```

### Arrêter un service en particulier
Référer vous au nom du service dans les fichier compose
```bash
docker compose down backend
```

