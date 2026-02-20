from confs.main import app

from . import simple

# faire les autres imports des fichiers de tasks ici
# pour qu'ils soient pris en compte

celery_app = app.extensions['celery']
