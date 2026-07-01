import logging
logging.disable(logging.CRITICAL)

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework.test import APIClient
from unittest import mock

from users.models import BaseProfile
from tm_bot.models import OrdersBot, MessengerAccount
from promos.models import Campaign, CampaignOpenEvent

User = get_user_model()


class TelegramAuthViewTests(TestCase):
    """
    Интеграционные тесты для /api/v1/tmauth/.

    Покрываем:
    * создание нового пользователя + MessengerAccount через Mini App
    * поведение с пустыми и «странными» именами
    * учёт рекламной кампании (Campaign / CampaignOpenEvent)
    * повторный логин без дублирования аккаунтов и new_users
    """

    def setUp(self):
        self.client = APIClient()
        self.url = "/api/v1/tmauth/"

        # Минимальный OrdersBot, чтобы кампания могла к нему привязаться
        self.bot = OrdersBot.objects.create(
            msngr_type="tm",
            name="Test TG Bot",
            source_id="test-source",
            city="Beograd",
            link="https://t.me/test_bot",
            frontend_link="https://frontend.example/test_bot",
            is_active=True,
        )

    # ------------------------------------------------------------------
    # HELPERS
    # ------------------------------------------------------------------

    def _tg_user(self, **override):
        base = {
            "id": 795798555515,
            "is_bot": False,
            "first_name": "Natalia",
            "last_name": "Kirillova",
            "username": "Gatitka5",
            "allows_write_to_pm": True,
            "language_code": "ru",
            "photo_url": "https://t.me/i/userpic/320/somepic.svg",
        }
        base.update(override)
        return base

    # ------------------------------------------------------------------
    # 0) ПРОСТО УСПЕШНЫЙ КЕЙС БЕЗ КАМПАНИИ
    # ------------------------------------------------------------------

    @override_settings(
        TELEGRAM_BOT_TOKEN_BG="TEST_BOT_BG",
        TELEGRAM_BOT_TOKEN_NS="TEST_BOT_NS",
    )
    @mock.patch("api.views.verify_telegram_payload")
    def test_tmauth_happy_path_basic_user(self, mock_verify):
        """
        Базовый успешный кейс:
        - обычный Telegram-пользователь с нормальными именами (латиница)
        - без рекламной кампании

        Ожидаем:
        * 200 OK и пара токенов (access/refresh)
        * создаются MessengerAccount, WEBAccount, BaseProfile
        * first_name/last_name в profile и web-аккаунте такие же, как пришли из tg
        * никаких Campaign / CampaignOpenEvent не создаётся
        """
        tg = self._tg_user()  # дефолтные нормальные имена: Natalia / Kirillova
        mock_verify.return_value = {"user": tg}

        payload = {
            "initdata": "dummy-init-data",
            "city": "Beograd",
            # без "campaign"
        }

        resp = self.client.post(self.url, payload, format="json")
        self.assertEqual(resp.status_code, 200, resp.data)
        self.assertIn("access", resp.data)
        self.assertIn("refresh", resp.data)

        # --- аккаунты создались один раз ---

        self.assertEqual(MessengerAccount.objects.count(), 1)
        self.assertEqual(BaseProfile.objects.count(), 1)
        self.assertEqual(User.objects.count(), 1)

        msngr = MessengerAccount.objects.get(msngr_id=str(tg["id"]))
        self.assertEqual(msngr.msngr_type, "tm")
        self.assertEqual(msngr.msngr_first_name, tg["first_name"])
        self.assertEqual(msngr.msngr_last_name, tg["last_name"])
        self.assertEqual(msngr.msngr_username, tg["username"])
        self.assertEqual(msngr.city, "Beograd")

        base_profile = msngr.profile
        user = base_profile.web_account

        # В happy-path имена проходят валидацию и попадают в профиль и web-аккаунт как есть
        self.assertEqual(base_profile.first_name, tg["first_name"])
        self.assertEqual(base_profile.last_name, tg["last_name"])
        self.assertEqual(user.first_name, tg["first_name"])
        self.assertEqual(user.last_name, tg["last_name"])

        # Никаких кампаний/событий не создавалось
        self.assertEqual(Campaign.objects.count(), 0)
        self.assertEqual(CampaignOpenEvent.objects.count(), 0)

    # ------------------------------------------------------------------
    # 1) НОВЫЙ ПОЛЬЗОВАТЕЛЬ, ПУСТЫЕ ИМЕНА (без кампании)
    # ------------------------------------------------------------------

    @override_settings(
        TELEGRAM_BOT_TOKEN_BG="TEST_BOT_BG",
        TELEGRAM_BOT_TOKEN_NS="TEST_BOT_NS",
    )
    @mock.patch("api.views.verify_telegram_payload")
    def test_tmauth_new_user_with_empty_names(self, mock_verify):
        """
        Первый логин нового Telegram-пользователя с пустыми именами.

        Ожидаем:
        * создаются MessengerAccount, WEBAccount и BaseProfile
        * в MessengerAccount имена сохраняются как пришли из Telegram (пустые строки)
        * в BaseProfile / WEBAccount имена остаются пустыми строками
        """
        tg = self._tg_user(first_name="", last_name="", username="")
        mock_verify.return_value = {"user": tg}

        payload = {
            "initdata": "dummy-init-data",
            "city": "Beograd",
        }

        resp = self.client.post(self.url, payload, format="json")
        self.assertEqual(resp.status_code, 200, resp.data)

        # MessengerAccount создан
        msngr = MessengerAccount.objects.get(msngr_id=str(tg["id"]))
        self.assertEqual(msngr.msngr_type, "tm")
        self.assertEqual(msngr.msngr_first_name, "")
        self.assertEqual(msngr.msngr_last_name, "")
        self.assertEqual(msngr.msngr_username, "")

        # Создан web-аккаунт + base_profile
        base_profile = msngr.profile  # reverse-связь BaseProfile -> MessengerAccount
        user = base_profile.web_account

        self.assertEqual(user.first_name, "")
        self.assertEqual(user.last_name, "")
        self.assertEqual(base_profile.first_name, "")
        self.assertEqual(base_profile.last_name, "")

    # ------------------------------------------------------------------
    # 2) НОВЫЙ ПОЛЬЗОВАТЕЛЬ, «СТРАННЫЕ» ИМЕНА + РЕКЛАМНАЯ КАМПАНИЯ
    # ------------------------------------------------------------------

    @override_settings(
        TELEGRAM_BOT_TOKEN_BG="TEST_BOT_BG",
        TELEGRAM_BOT_TOKEN_NS="TEST_BOT_NS",
    )
    @mock.patch("api.views.verify_telegram_payload")
    def test_tmauth_creates_new_user_with_weird_names_and_campaign(
        self, mock_verify
    ):
        """
        Новый пользователь заходит по рекламной кампании, в имени есть emoji/спецсимволы.

        Ожидаем:
        * MessengerAccount хранит «сырые» данные из Telegram (включая emoji)
        * WEBAccount/BaseProfile — очищенные имена (пустые строки),
          чтобы не ломать валидацию
        * по Campaign:
            - new_users увеличился на 1
            - создан один CampaignOpenEvent с нужными связями
        """
        special_name = "Nataliaאָלֶף־בֵּית עִבְרִ🔥"

        tg = self._tg_user(
            first_name=special_name,
            last_name=special_name,
            username="Gatitka5",
        )
        mock_verify.return_value = {"user": tg}

        # Кампания с известным кодом (ВАЖНО: не больше 10 символов)
        campaign_code = "zsWAhYMj7i"  # 10 символов
        campaign = Campaign.objects.create(
            name="Test campaign",
            code=campaign_code,
            city="Beograd",
            bot=self.bot,
            new_users=0,
        )

        payload = {
            "initdata": "dummy-init-data",
            "city": "Beograd",
            "campaign": campaign_code,
        }

        resp = self.client.post(self.url, payload, format="json")
        self.assertEqual(resp.status_code, 200, resp.data)

        # MessengerAccount с «сырыми» именами
        msngr = MessengerAccount.objects.get(msngr_id=str(tg["id"]))
        self.assertEqual(msngr.msngr_first_name, special_name)
        self.assertEqual(msngr.msngr_last_name, special_name)
        self.assertEqual(msngr.msngr_username, tg["username"])

        # WEBAccount / BaseProfile — очищенные имена
        base_profile = msngr.profile
        user = base_profile.web_account
        self.assertEqual(user.first_name, "")
        self.assertEqual(user.last_name, "")
        self.assertEqual(base_profile.first_name, "")
        self.assertEqual(base_profile.last_name, "")

        # Кампания: один новый пользователь и один переход
        campaign.refresh_from_db()
        self.assertEqual(campaign.new_users, 1)
        events = CampaignOpenEvent.objects.filter(campaign=campaign, user=msngr)
        self.assertEqual(events.count(), 1)

    # ------------------------------------------------------------------
    # 3) ПОВТОРНЫЙ ЛОГИН НЕ СОЗДАЁТ ДУБЛИКАТОВ И NEW_USERS
    # ------------------------------------------------------------------

    @override_settings(
        TELEGRAM_BOT_TOKEN_BG="TEST_BOT_BG",
        TELEGRAM_BOT_TOKEN_NS="TEST_BOT_NS",
    )
    @mock.patch("api.views.verify_telegram_payload")
    def test_tmauth_second_login_does_not_create_duplicates_and_new_users(
        self, mock_verify
    ):
        """
        Один и тот же Telegram-пользователь логинится по одной и той же
        рекламной кампании два раза.

        Ожидаем:
        * MessengerAccount / WEBAccount / BaseProfile создаются только один раз
        * Campaign.new_users инкрементится только на первом заходе
        * записываются два CampaignOpenEvent (два перехода по ссылке)
        """
        tg = self._tg_user()
        mock_verify.return_value = {"user": tg}

        campaign_code = "relog12345"  # 10 символов
        campaign = Campaign.objects.create(
            name="Second login campaign",
            code=campaign_code,
            city="Beograd",
            bot=self.bot,
            new_users=0,
        )

        payload = {
            "initdata": "dummy-init-data",
            "city": "Beograd",
            "campaign": campaign_code,
        }

        # --- первый логин ---
        resp1 = self.client.post(self.url, payload, format="json")
        self.assertEqual(resp1.status_code, 200, resp1.data)

        msngr = MessengerAccount.objects.get(msngr_id=str(tg["id"]))
        base_profile = msngr.profile
        user = base_profile.web_account

        campaign.refresh_from_db()
        self.assertEqual(campaign.new_users, 1)
        self.assertEqual(
            CampaignOpenEvent.objects.filter(campaign=campaign, user=msngr).count(),
            1,
        )

        # --- второй логин тем же пользователем и по той же кампании ---
        resp2 = self.client.post(self.url, payload, format="json")
        self.assertEqual(resp2.status_code, 200, resp2.data)

        # Количество сущностей не меняется
        self.assertEqual(MessengerAccount.objects.count(), 1)
        self.assertEqual(User.objects.count(), 1)
        self.assertEqual(BaseProfile.objects.count(), 1)

        msngr.refresh_from_db()
        base_profile.refresh_from_db()
        user.refresh_from_db()

        # new_users не увеличивается повторно
        campaign.refresh_from_db()
        self.assertEqual(campaign.new_users, 1)

        # но фиксируем ещё один переход по ссылке
        events_qs = CampaignOpenEvent.objects.filter(campaign=campaign, user=msngr)
        self.assertEqual(events_qs.count(), 2)
