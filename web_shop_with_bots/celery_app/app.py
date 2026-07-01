import os
from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "web_shop_with_bots.settings")

app = Celery("web_shop_with_bots")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
