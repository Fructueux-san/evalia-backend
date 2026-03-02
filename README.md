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
>```bash
docker build -t evaluator-sklearn:latest -f artefacts/evaluator/Dockerfile.sklearn artefacts/evaluator 
docker build -t evaluator-tf:latest -f artefacts/evaluator/Dockerfile.tensorflow artefacts/evaluator
docker build -t evaluator-pt:latest -f artefacts/evaluator/Dockerfile.pytorch artefacts/evaluator
>```

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

NB: Si c'est pour la toute première fois, et que vous avez un problème du genre : 
`network evalia-net declared as external, but could not be found` utilisez la commande 
suivante pour régler le problème : `docker network create evalia-net`. 
Pour supprimer `docker network rm evalia-net`


## Les migration

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

## Accès à la base de données (possiblement utile en dev)
```bash
 docker exec -it database-evalia psql -U evalia evaliadb
```


## Flower 
L'app utilise celery avec redis pour les tâches async et queueing.
Il est accessible sur `http://localhost:5555` après le lancement du backend. 

Veuillez à ce que tous les services du docker compose soient lancés. 


## Tests 

Les tests d'API (`tests/APITesting.py`) sont lancés automatiquement **avant** le démarrage 
du serveur Flask (voir `init.sh`). Le serveur ne démarre que si tous les tests passent.

### Lancer les tests manuellement
```bash
# Dans le conteneur Docker :
docker exec -it backend-evalia python3 -m pytest -v tests/APITesting.py -o cache_dir=/tmp
```

Les tests sont **auto-suffisants** : ils créent leurs propres données (utilisateurs uniques) 
et les nettoient automatiquement. Aucune donnée préexistante n'est nécessaire.

Voir `tests/Readme.md` pour le détail des 18 tests couverts.


## Troubleshooting

### Le backend ne démarre pas (localhost:8000 ne répond pas)

1. **Vérifier les logs** : `docker logs backend-evalia -f`
2. **Si les tests échouent** : les logs montreront les tests pytest qui bloquent le démarrage.
   Le serveur ne se lance que si tous les tests passent.
3. **Si la DB n'est pas prête** : `init.sh` attend automatiquement que PostgreSQL soit accessible 
   (max 30 tentatives, 2s entre chaque). Vérifier que le conteneur `database-evalia` est running.
4. **Réseau Docker manquant** : si vous voyez `network evalia-net declared as external, but could not be found`, 
   lancez : `docker network create evalia-net`
5. **Reconstruire les images** : `docker compose -f docker-compose.dev.yaml up -d --build`

### Ports utilisés
| Port | Service |
|------|---------|
| 8000 | API Flask (principal) |
| 8001 | SSE (Server-Side Events) |
| 5555 | Flower (monitoring Celery) |
| 5433 | PostgreSQL (exposé en dev) |
| 6379 | Redis |


# Architecture 
Celery et redis sont utilisé pour récupérer des tâches à lancer en arrière plan
(comme l'exécution des modèles dans notre cas) ; 
et ensuite créer un environement de conteneur docker à la volé pour l'exécuton des 
modèles en sandbox. 

Il faut consulter la documentation suivante pour 
pousser les configurations de docker : 
https://docker-py.readthedocs.io/en/stable/containers.html

**Server-Side Event**
Le SSE permet à travers un canal uni-directionnel (server vers client) 
d'envoyer les notifications depuis un server vers un client. Il a été choisit 
parce qu'il va être moins gourmant en ressource par rapport à socket-io qui est bidirectionnel. 

Aussi, ces sockets etant des liaison permanente, le sse a été écrit dans une app 
Flask séparé démarrant avec un nbre de workers précis (en prod) pour éviter de consommer 
les worker gunicorn dans le processus app Flask principal. 

Cette Architecture modulaire va permettre, ici dans notre cas d'envoyer des notifications 
sse par le biais d'une fonction généric écrit, et se voit très utile depuis celery (vu que c'est asynchrone, 
on pourra notifier le user quand une task donne un résulat donné). 

Se référer à la documentation de flask-sse pour compréhension. 

**Snippet de code pour le frontend**
Le JS à écrire pour exploiter le sse ici va ressembler à ceci : 
```js

const source = new EventSource("/stream?channel=user:037b38e4-9df6-4b0d-9b1c-1832941257c5");

// Cas générique : tous les messages sans type spécifique
source.onmessage = (event) => {
  console.log("Reçu via onmessage:", event.data);
};

// Cas ciblé : uniquement les events de type "message"
source.addEventListener("message", (event) => {
  console.log("Reçu via type=message:", event.data);
});

// Tu pourrais aussi envoyer un type différent, ex. "notification"
source.addEventListener("notification", (event) => {
  console.log("Notif:", event.data);
});
```

L'uuid spécifié dans ce snippet est celui du user connecté, donc obtenu après son login. 




