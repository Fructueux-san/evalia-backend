from celery import shared_task
from tasks.eval_helper import evaluate_submission

@shared_task(name="tensorflow_evaluation")
def run_tensorflow_evaluation(submission_id):
    return evaluate_submission(
        submission_id=submission_id,
        image_name="evaluator-tensorflow:latest",
        container_model_name="model.h5"
    )
