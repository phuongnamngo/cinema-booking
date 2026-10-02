import logging

from celery import shared_task

from .services import apply_gateway_query, payments_due_for_reconcile

logger = logging.getLogger(__name__)


@shared_task(name="payments.reconcile_pending")
def reconcile_pending_payments():
    due = list(payments_due_for_reconcile())
    for payment in due:
        apply_gateway_query(payment)
    if due:
        logger.info("Đối soát %s payment pending", len(due))
    return len(due)
