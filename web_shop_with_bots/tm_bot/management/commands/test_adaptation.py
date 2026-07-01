from django.core.management.base import BaseCommand
from django.conf import settings
from django.db import transaction
from django.db.models import Q
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission, Group
from django.contrib.contenttypes.models import ContentType

from promos.models import Campaign, PromoBroadcast
from tm_bot.models import AdminChatTM, OrdersBot, MessengerAccount
from users.models import BaseProfile, get_or_create_dummy_webacount_and_baseprofile


class Command(BaseCommand):
    help = (
        "Единоразовая адаптация БД под текущие настройки:\n"
        "- обновить чат-ид админских чатов из settings.ADMIN_CHATS\n"
    )

    def handle(self, *args, **options):

        self.new_data = {
            "Beograd": {
                "name": "YUME_SUSHI_test_2_bot",
                "link": "https://t.me/YUME_SUSHI_test_2_bot",
                "campaign": "78cexaiigs"
            },
            "NoviSad": {
                "name": "YUME_SUSHI_test_1_bot",
                "link": "https://t.me/YUME_SUSHI_test_1_bot",
                "campaign": "TAuywvlZRq"
            }
        }
        self.admin_id = 194602954

        self.stdout.write(self.style.MIGRATE_HEADING("Запуск test_adoptation..."))

        self._update_admin_chats()
        self._update_ordersbots()
        self._create_campaigns()
        self._create_city_permissions()
        self._grant_admin_group_promos_permissions()

        self.stdout.write(self.style.MIGRATE_HEADING(
            "Начинаем нормализацию MessengerAccount..."
        ))
        self.step_1_clear_msngr_link_for_empty_username()
        self.step_2_fix_usernames_without_at()
        self.step_3_sync_registered_and_subscription_for_linked()
        self.step_4_create_dump_accounts_for_unlinked()

        self.stdout.write(self.style.SUCCESS("test_adoptation завершён."))

    def _update_admin_chats(self):
        """
        Обновляем AdminChat.chat_id из settings.ADMIN_CHATS[city]
        """
        self.stdout.write("Шаг 1: обновление admin chats...")

        updated = 0
        skipped = 0

        with transaction.atomic():
            for chat in AdminChatTM.objects.all():
                city = chat.city
                new_chat_id = settings.ADMIN_CHATS.get(city)

                if new_chat_id is None:
                    skipped += 1
                    self.stdout.write(
                        self.style.WARNING(
                            f"  нет значения в ADMIN_CHATS для города '{city}', пропускаю"
                        )
                    )
                    continue

                # если уже совпадает — не трогаем
                if getattr(chat, "chat_id", None) == new_chat_id:
                    continue

                chat.chat_id = new_chat_id
                chat.save(update_fields=["chat_id"])
                updated += 1

        self.stdout.write(
            f"  AdminChat обновлено: {updated}, пропущено (нет ключа в settings): {skipped}"
        )

    def _update_ordersbots(self):
        """
        Обновляем OrdersBot.name+frontend_link
        """
        self.stdout.write("Шаг 1: обновление orderbots...")

        updated = 0
        skipped = 0

        with transaction.atomic():
            for bot in OrdersBot.objects.all():
                city = bot.city
                new_city_data = self.new_data.get(city)

                if new_city_data is None:
                    skipped += 1
                    self.stdout.write(
                        self.style.WARNING(
                            f"  нет значения в test_admin_city для города '{city}', пропускаю"
                        )
                    )
                    continue

                bot.name = new_city_data['name']
                bot.link = new_city_data['link']
                bot.frontend_link = f"{bot.link}?start={new_city_data['campaign']}"
                bot.admin_id = self.admin_id
                bot.save(update_fields=["name", "link", "frontend_link", "admin_id"])
                updated += 1

        self.stdout.write(
            f"  OrdersBot обновлено: {updated}, пропущено: {skipped}"
        )

    def _create_campaigns(self):
        """
        Создаём Campaign для каждого тестового города из self.new_data
        с кодом, равным значению `campaign` (start-параметр).
        """
        self.stdout.write("Шаг 3: создание Campaign...")

        created = 0
        skipped = 0

        with transaction.atomic():
            for city, data in self.new_data.items():
                code = data["campaign"]

                # находим соответствующий бот
                bot = OrdersBot.objects.filter(city=city).first()
                if not bot:
                    skipped += 1
                    self.stdout.write(
                        self.style.WARNING(
                            f"  не найден OrdersBot для города '{city}', пропускаю"
                        )
                    )
                    continue

                # формируем ссылку для кампании (совпадает с frontend_link бота)
                link = f"{bot.link}?start={code}"

                # создаём кампанию, если такой code ещё нет
                campaign, created_flag = Campaign.objects.get_or_create(
                    code=code,
                    defaults={
                        "name": f"Test campaign {city}",
                        "city": city,
                        "link": link,
                        "bot": bot,
                    },
                )

                if created_flag:
                    created += 1
                else:
                    # если вдруг она уже есть — можно при желании обновлять link/bot
                    # campaign.link = link
                    # campaign.bot = bot
                    # campaign.save(update_fields=["link", "bot"])
                    skipped += 1
                    self.stdout.write(
                        self.style.WARNING(
                            f"  Campaign с кодом '{code}' уже существует, пропускаю создание"
                        )
                    )
        self.stdout.write(
            f"  Campaign создано: {created}, пропущено: {skipped}"
        )

    def _create_city_permissions(self):
        """
        Создаём персонифицированные по городу права:
        - promos.change_campaign_Beograd / promos.change_campaign_NoviSad
        - promos.change_promobroadcast_Beograd / promos.change_promobroadcast_NoviSad

        И выдаём их админам соответствующего города (is_staff=True, role='admin').
        """
        self.stdout.write("Создание и раздача городских прав для Campaign/PromoBroadcast...")

        User = get_user_model()
        cities = ["Beograd", "NoviSad"]

        perms_created = 0
        perms_existing = 0
        users_updated = 0

        # content_types для моделей
        ct_campaign = ContentType.objects.get_for_model(Campaign)
        ct_broadcast = ContentType.objects.get_for_model(PromoBroadcast)

        # чтобы потом легко взять нужное право по городу
        campaign_perms_by_city = {}
        broadcast_perms_by_city = {}

        with transaction.atomic():
            # 1) создаём права
            for city in cities:
                # --- Campaign ---
                camp_codename = f"change_campaign_{city}"
                camp_name = f"Can change Campaign {city}"  # по аналогии с OrdersBot

                camp_perm, created = Permission.objects.get_or_create(
                    content_type=ct_campaign,
                    codename=camp_codename,
                    defaults={"name": camp_name},
                )
                campaign_perms_by_city[city] = camp_perm
                if created:
                    perms_created += 1
                else:
                    perms_existing += 1

                # --- PromoBroadcast ---
                pb_codename = f"change_promobroadcast_{city}"
                pb_name = f"Can change PromoBroadcast {city}"

                pb_perm, created = Permission.objects.get_or_create(
                    content_type=ct_broadcast,
                    codename=pb_codename,
                    defaults={"name": pb_name},
                )
                broadcast_perms_by_city[city] = pb_perm
                if created:
                    perms_created += 1
                else:
                    perms_existing += 1

            # 2) выдаём права пользователям-админам
            for city in cities:
                camp_perm = campaign_perms_by_city[city]
                pb_perm = broadcast_perms_by_city[city]

                admins_qs = User.objects.filter(
                    is_staff=True,
                    role="admin",
                    city=city,
                )

                for user in admins_qs:
                    # add() сам не добавит дубликат, если уже есть
                    user.user_permissions.add(camp_perm, pb_perm)
                    users_updated += 1

        self.stdout.write(
            f"  Прав создано: {perms_created}, уже существовало: {perms_existing}, "
            f"админов с обновлёнными правами: {users_updated}"
        )

    def _grant_admin_group_promos_permissions(self):
        """
        Даём группе auth_group.name='admin' (id=1) права на:
        - promos.Campaign: view/add/delete
        - promos.PromoBroadcast: view/add/delete

        Нужно чтобы админы могли видеть/создавать/удалять источники и рассылки.
        """
        self.stdout.write("Выдача прав группе 'admin' на Campaign/PromoBroadcast...")

        admin_group = Group.objects.filter(name="admin").first()
        if not admin_group:
            self.stdout.write(self.style.WARNING("  Группа 'admin' не найдена, пропускаю."))
            return

        ct_campaign = ContentType.objects.get_for_model(Campaign)
        ct_broadcast = ContentType.objects.get_for_model(PromoBroadcast)

        needed = [
            (ct_campaign, "view_campaign"),
            (ct_campaign, "add_campaign"),
            (ct_campaign, "delete_campaign"),
            (ct_broadcast, "view_promobroadcast"),
            (ct_broadcast, "add_promobroadcast"),
            (ct_broadcast, "delete_promobroadcast"),
        ]

        perms = []
        missing = []

        for ct, codename in needed:
            perm = Permission.objects.filter(content_type=ct, codename=codename).first()
            if perm:
                perms.append(perm)
            else:
                missing.append(codename)

        with transaction.atomic():
            if perms:
                admin_group.permissions.add(*perms)

        if missing:
            self.stdout.write(self.style.WARNING(f"  Не найдены permissions: {missing}"))
        self.stdout.write(self.style.SUCCESS(f"  Группе 'admin' выдано прав: {len(perms)}"))

    # 1. msngr_link сделать пустым, где msngr_username == ''/None
    def step_1_clear_msngr_link_for_empty_username(self):
        self.stdout.write("Шаг 1: очистка msngr_link при пустом username...")

        qs = MessengerAccount.objects.filter(
            Q(msngr_username__isnull=True) | Q(msngr_username="")
        ).exclude(msngr_link="")

        with transaction.atomic():
            updated = qs.update(msngr_link="")

        self.stdout.write(
            f"  Обновлено записей: {updated}"
        )

    # 2. переписать msngr_username 'tm' без @ в начале
    def step_2_fix_usernames_without_at(self):
        self.stdout.write("Шаг 2: удаляем '@' в msngr_username для msngr_type='tm'...")

        qs = MessengerAccount.objects.filter(
            msngr_type="tm",
            msngr_username__startswith="@",
        )

        counter = 0
        with transaction.atomic():
            for ma in qs.iterator():
                old_username = ma.msngr_username
                ma.msngr_username = ma.msngr_username.lstrip("@")
                ma.save(update_fields=["msngr_username"])
                counter += 1

        self.stdout.write(
            f"  Пользователей с исправленным username: {counter}"
        )

    # 3. registered=True, если messenger_account привязан к base_profile.
    #    subscription взять из base_profile.web_account.is_subscribed
    def step_3_sync_registered_and_subscription_for_linked(self):
        self.stdout.write(
            "Шаг 3: registered/subscription для MA, привязанных к BaseProfile..."
        )

        qs = (
            BaseProfile.objects
            .select_related("web_account", "messenger_account")
            .filter(messenger_account__isnull=False)
        )

        updated = 0
        without_web = 0

        with transaction.atomic():
            for bp in qs.iterator():
                ma = bp.messenger_account
                if not ma:
                    continue

                ma.registered = True

                if bp.web_account:
                    # поле в WEBAccount — is_subscribed
                    ma.subscription = bp.web_account.is_subscribed
                else:
                    # на всякий случай отметим, чтобы можно было глянуть в лог
                    without_web += 1

                ma.save(update_fields=["registered", "subscription"])
                updated += 1

        self.stdout.write(
            f"  Обновлено MA: {updated} (без web_account: {without_web})"
        )

    def step_4_create_dump_accounts_for_unlinked(self):
        self.stdout.write(
            "Шаг 4: dump-аккаунты для MA без привязки к BaseProfile..."
        )

        qs = MessengerAccount.objects.filter(profile__isnull=True)

        created_dump = 0
        orders_moved = 0

        for ma in qs.iterator():
            with transaction.atomic():
                # ключевая правка: subscription=True
                ma.registered = False
                ma.subscription = True
                ma.save(update_fields=["registered", "subscription"])

                tg = {
                    "id": ma.msngr_id,
                    "first_name": ma.msngr_first_name or "",
                    "last_name": ma.msngr_last_name or "",
                }

                user = get_or_create_dummy_webacount_and_baseprofile(ma, tg)
                base_profile = user.base_profile
                created_dump += 1

                # 🔹 НОВОЕ: переносим дату создания из MessengerAccount
                # в WEBAccount.date_joined и BaseProfile.date_joined
                if ma.created:
                    # Обновляем дату регистрации веб-аккаунта
                    user.date_joined = ma.created
                    user.save(update_fields=["date_joined"])

                    # Обновляем дату регистрации базового профиля
                    base_profile.date_joined = ma.created
                    base_profile.save(update_fields=["date_joined"])

                if hasattr(ma, "orders") and ma.orders.exists():
                    order = ma.orders.first()
                    if hasattr(order, "transit_all_msngr_orders_to_base_profile"):
                        order.transit_all_msngr_orders_to_base_profile(base_profile)
                        orders_moved += ma.orders.count()

        self.stdout.write(
            f"  Создано/подвязано dump-профилей: {created_dump}, "
            f"перенесено заказов (примерно): {orders_moved}"
        )
