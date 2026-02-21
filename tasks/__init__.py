from confs.main import app

from . import simple

# faire les autres imports des fichiers de tasks ici
# pour qu'ils soient pris en compte
from . import onnx_eval
from . import pytorch_eval
from . import sklearn_eval
from . import tensorflow_eval

celery_app = app.extensions['celery']
