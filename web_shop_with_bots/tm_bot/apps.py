from django.apps import AppConfig


class TmBotConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'tm_bot'
    verbose_name = '3. Мессенджер'

    def ready(self):
        import tm_bot.signals
