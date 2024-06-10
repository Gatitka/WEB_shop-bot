from celery import shared_task
from django.utils import timezone
from rest_framework_simplejwt.token_blacklist import models
import logging


logger = logging.getLogger(__name__)


@shared_task
def delete_expired_tokens():
    delete_exp_blcklist_tokens()
    delete_exp_outstd_tokens()
    logger.info('expired_tokens удалены.')


def delete_exp_blcklist_tokens():
    expired_blck_tokens = models.BlacklistedToken.objects.filter(
        token__expires_at__lt=timezone.now())
    for blcklist_token in expired_blck_tokens:
        outst_token = blcklist_token.token
        blcklist_token.delete()
        outst_token.delete()
    logger.info('Expired BlacklistedToken, OutstandingToken удалены.')


def delete_exp_outstd_tokens():
    expired_outstd_tokens = models.OutstandingToken.objects.filter(
        expires_at__lt=timezone.now())
    expired_outstd_tokens.delete()
    logger.info('Expired OutstandingToken удалены.')
