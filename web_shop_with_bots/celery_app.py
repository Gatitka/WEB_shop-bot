# import os
# import time

# from celery import Celery
# from celery.schedules import crontab
# from django.conf import settings
# import subprocess
# from datetime import datetime

# os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'web_shop_with_bots.settings')

# app = Celery('web_shop_with_bots')
# app.config_from_object('django.conf:settings')
# app.conf.broker_url = settings.CELERY_BROKER_URL
# app.conf.enable_utc = False
# app.conf.timezone = 'Europe/Belgrade'
# app.autodiscover_tasks()


# @app.task()
# def debug_task():
#     time.sleep(20)
#     print('Hello from debug_task')


# @app.task()
# def backup_database_celeryfile():
#     # Получите текущую дату для имени файла
#     current_date = datetime.now().strftime('DB_backup %Y.%m.%d %H-%M-%S')
#     backup_file = f"/backups/db_backup_{current_date}.sql"

#     # Создайте команду для выполнения бэкапа
#     command = (f"sudo docker compose -f docker-compose.test_server_cache.yml "
#                f"exec db pg_dump -h db -U postgres -d yume_db -F c -b -v -f "
#                f"{backup_file}")

#     # Выполните команду
#     result = subprocess.run(command, shell=True,
#                             env={"PGPASSWORD": settings.POSTGRES_PASSWORD })

#     # Проверьте результат
#     if result.returncode == 0:
#         print(f"Backup successful: {backup_file}")
#     else:
#         print(f"Backup failed: {result.stderr}")


# # Определение периодической задачи, которая будет запускаться ночью
# app.conf.beat_schedule = {
#     'run-nightly-task': {
#         'task': 'users.tasks.delete_expired_tokens',
#         'schedule': crontab(hour=14, minute=30),
#     },
#     'backup-database-every-day': {
#         'task': 'celery_app.backup_database_celeryfile',
#         'schedule': crontab(hour=0, minute=0),
#     }
# }
