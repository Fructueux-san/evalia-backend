from confs.main import celery
from celery import shared_task



@celery.task
def divide(x, y):
    import time
    time.sleep(5)
    return x / y

# Pour voir si les shared task marchent aussi (histore de ne pas)
# impoorter l'objet depuis confs.main
@shared_task(name="task_2")
def divide_2(x, y):
    import time
    time.sleep(5+2)
    return x / y
