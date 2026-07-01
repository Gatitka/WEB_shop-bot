from django.contrib.admin import SimpleListFilter


class BaseBotWriteFilter(SimpleListFilter):
    """
    Фильтр вида:
      Бот N — может / не может / неизвестно (+ показывает количества)
    """
    bot_id: int = None           # переопределим в наследниках
    bot_label: str = None        # опционально: текст в админке

    def lookups(self, request, model_admin):
        # Только статусы, без повторения имени бота и без (count)
        return (
            ("true",  "✅ может писать"),
            ("false", "❌ не может"),
            ("none",  "❓ неизвестно"),
        )

    def queryset(self, request, queryset):
        val = self.value()
        if not val:
            return queryset

        if val == "true":
            return queryset.filter(
                bot_links__bot_id=self.bot_id,
                bot_links__tg_can_write=True
            ).distinct()

        if val == "false":
            return queryset.filter(
                bot_links__bot_id=self.bot_id,
                bot_links__tg_can_write=False
            ).distinct()

        if val == "none":
            return queryset.filter(
                bot_links__bot_id=self.bot_id,
                bot_links__tg_can_write__isnull=True
            ).distinct()

        return queryset


class Bot1WriteFilter(BaseBotWriteFilter):
    title = "Бот Beograd"
    parameter_name = "bot1_write"
    bot_id = 1


class Bot2WriteFilter(BaseBotWriteFilter):
    title = "Бот NoviSad"
    parameter_name = "bot2_write"
    bot_id = 2
