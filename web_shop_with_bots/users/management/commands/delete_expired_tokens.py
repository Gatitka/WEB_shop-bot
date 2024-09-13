from django.core.management import BaseCommand
import logging
from rest_framework_simplejwt.token_blacklist import models
from django.utils import timezone


logger = logging.getLogger(__name__)


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


class Command(BaseCommand):
    help = ("Delete expired tokens. Delete expired blacklisted tokens, ",
            "then delete expired outstanding tokens.")

    def handle(self, *args, **options):

        try:
            delete_exp_blcklist_tokens()
            delete_exp_outstd_tokens()
            logger.info('Expired_tokens deleted successfully.')

        except Exception as e:
            logger.error(f"Expired_tokens clean up error: {e}")
