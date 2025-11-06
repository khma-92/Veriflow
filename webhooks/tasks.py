from celery import shared_task
import math
from django.db import transaction
from .models import WebhookConfig
from .services.sender import send_webhook

@shared_task(bind=True, max_retries=10, default_retry_delay=5)
def deliver_webhook_task(self, config_id: int, event: str, data: dict, attempt: int = 1):
    """
    Tâche Celery avec retry exponentiel.
    """
    try:
        config = WebhookConfig.objects.select_related("tenant").get(id=config_id, active=True)
    except WebhookConfig.DoesNotExist:
        return

    delivery = send_webhook(config, event, data, attempt=attempt)
    if delivery.ok:
        return

    # planifie retry si on n'a pas dépassé max_retries configuré
    max_r = config.max_retries or 0
    if attempt >= max_r:
        return

    backoff = config.backoff_s or 5
    next_delay = int(backoff * math.pow(2, attempt - 1))  # 5,10,20,40...
    raise self.retry(countdown=next_delay, kwargs={"config_id": config_id, "event": event, "data": data, "attempt": attempt + 1})
