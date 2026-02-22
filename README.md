# evalia-backend

Backend de la plateforme de suivi et d'évaluation des modèles d'IA
dans un contexte de compétition 

## Technologies 
API écrit en Python (Flask), avec un peu de docker (via compose), 
une DB Postgresql et du scripting bash

## Au préalable ...
Il faut faire le build des images d'isolation sur la machine hôte.
Le build permet que les worker celery ne les build pas à chaque fois et fasse 
des installation coûteuses.
Donc, c'est un run sur image à froid.
**Commande :** `./artefacts/builder.sh`

Il faut le faire avec le script builder dans le dossier artefact
(nb: c'est un script bash, donc si vous êtes sur windows, vous pouvez proposer 
un script batch extension .bat).

> Si vous avez la commande docker installé sur votre machine
> et que c'est windows que vous utilisé vous pouvez faire un build manuel. 
```bash
docker build -t evaluator-sklearn:latest -f artefacts/evaluator/Dockerfile.sklearn artefacts/evaluator 
docker build -t evaluator-tf:latest -f artefacts/evaluator/Dockerfile.tensorflow artefacts/evaluator
docker build -t evaluator-pt:latest -f artefacts/evaluator/Dockerfile.pytorch artefacts/evaluator
```

---

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


## Flower 
L'app utilise celery avec redis pour les tâches async et queueing.
Il est accessible sur `http://localhost:5555` après le lancement du backend. 

Veuillez à ce que tous les services du docker compose soient lancés. 


# Architecture 
Celery et redis sont utilisé pour récupérer des tâches à lancer en arrière plan
(comme l'exécution des modèles dans notre cas) ; 
et ensuite créer un environement de conteneur docker à la volé pour l'exécuton des 
modèles en sandbox. 

