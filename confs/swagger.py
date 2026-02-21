"""
Ici gît la configuration de la documentation de Swagger.
Il contient les paramètres de configuration de la doc.
"""

swagger_template = {
        "swagger": "2.0",
        "info": {
            "title": "Gestion des notes",
            "description": "Documentation d'API du backend de la gestion des notes.",
            "contact": {
                "name": "Developper",
                "email": "stanislas.houeto@uac.bj",
                "url": "https://uac.bj",
            },
            "termsOfService": "Terms of services",
            "version": "1.0",
            "host":"gestion-note",
            "basePath":"http://localhost:9000",
            "license":{
                "name":"License of API",
                "url":"API license URL"
            }
        },
    "schemes": [
        "http",
        "https"
    ],
}


swagger_config = {
    "headers": [
        ('Access-Control-Allow-Origin', '*'),
        # ('Access-Control-Allow-Methods', "GET, POST"),
    ],
    "specs": [
        {
            "endpoint": 'backend-note',
            "route": '/backend-note.json',
            "rule_filter": lambda rule: True,
            "model_filter": lambda tag: True,
        }
    ],
    "static_url_path": "/flasgger_static",
    "swagger_ui": True,
    "specs_route": "/apidocs/",
    "securityDefinitions": {
        "apiKey": {
            "type": "apiKey",
            "name": "Authorization",
            "in": "header",
            "description": "Ajoutez 'Bearer ' suivi de votre token JWT"
        }
    },
    "security": [
        {"apiKey": []}
    ]
    
}
