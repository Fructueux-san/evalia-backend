# evalia-backend

Backend de la plateforme de suivi et d'évaluation des modèles d'IA
dans un contexte de compétition 

## Technologies 
API écrit en Python (Flask), avec un peu de docker (via compose), 
une DB Postgresql et du scripting bash




## Pour lancer le projet 

1. **En production**
```bash
docker compose up -d 

```
2. **En dev**
```bash
docker compose -f docker-compose.dev.yaml up -d 
```

... ensuite 

### Les migration

```bash
docker exec -it backend-evalia flask db init # A faire une seule fois
docker exec -it backend-evalia flask db migrate # Lancer tout les migrations (a faire généralement une fois) 
docker exec -it backend-evalia flask db upgrade # Quand on met à jour un model et on veux répercuper sur la base

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

