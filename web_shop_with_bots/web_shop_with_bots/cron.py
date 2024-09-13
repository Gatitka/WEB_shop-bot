from datetime import datetime
from django.core.management import call_command
from django.utils import timezone
from rest_framework_simplejwt.token_blacklist import models
import logging
from django.conf import settings


logger = logging.getLogger(__name__)


def backup_database():
    # Получите текущую дату для имени файла
    current_date = datetime.now().strftime('%Y-%m-%d')
    backup_file = f"/backups/db_backup_{current_date}.dump"

    # Создайте команду для выполнения бэкапа
    # command = ("sudo docker compose -f ",
    #            f"{settings.DOCKER_COMPOSE_NAME} ",
    #            "exec db sh -c ",
    #            f"'pg_dump -U {settings.POSTGRES_USER} ",
    #            f"-d {settings.POSTGRES_DB} -F c -b -v -f {backup_file}'")
    command = (f"'pg_dump -U {settings.POSTGRES_USER} ",
               f"-d {settings.POSTGRES_DB} -F c -b -v -f {backup_file}'")
    full_command = " ".join(command)
    logger.info(f"full_command{full_command}")
    # Выполните команду
    try:
        call_command(full_command)
        logger.info(f"Backup successful: {backup_file}")

    except Exception as e:
        logger.error(f"Backup failed: {e}")


# production \     docker compose -f docker-compose.production_cache_crontab.yml exec db sh -c 'pg_dump -U postgres -d yume_db -F c -b -v -f /backups/db_backups_27-05-2024.sql'
# test_server \     docker compose -f /root/YUME_SUSHI/docker-compose.test_server_cache_crontab.yml exec db sh -c 'pg_dump -U postgres -d yume_db -F c -b -v -f /backups/db_backups_27-05-2024.sql'
# local\  pg_dump -U postgres -d yume_db -F c -b -v -f /backups/db_backup_today.dump

def delete_expired_tokens():

    try:
        delete_exp_blcklist_tokens()
        delete_exp_outstd_tokens()
        logger.info('Expired_tokens deleted successfully.')

    except Exception as e:
        logger.error(f"Expired_tokens clean up error: {e}")


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
