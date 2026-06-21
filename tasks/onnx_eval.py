from celery import shared_task
from tasks.eval_helper import evaluate_submission

@shared_task(name="onnx_evaluation")
def run_onnx_evaluation(submission_id):
    return evaluate_submission(
        submission_id=submission_id,
        image_name="evaluator-onnx:latest",
        container_model_name="model.onnx"
    )
