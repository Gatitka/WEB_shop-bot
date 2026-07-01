import logging
# logging.disable(logging.CRITICAL)
logger = logging.getLogger(__name__)

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework.test import APIClient
from unittest import mock

from shop.models import Order
from users.models import BaseProfile, UserAddress
from tm_bot.models import MessengerAccount, OrdersBot
from datetime import time

from django.db import IntegrityError

User = get_user_model()

# валидные тестовые номера
WTS_MAIN = "+381601234567"
WTS_NEW = "+381601234568"


class MeBasicFieldsTests(TestCase):
    """
    Финальный набор тестов:
    — базовые поля
    — ошибки валидации
    — WhatsApp
    — Telegram (включая спецсимволы, пустые строки и смену города)
    """

    # ------------------------------------------------------------------
    # SETUP
    # ------------------------------------------------------------------

    def setUp(self):
        self.client = APIClient()

        OrdersBot.objects.create(
            msngr_type="tm",
            name="Test bot",
            city="Beograd",
            source_id="test-source",
            admin_id="123456",
        )

        self.user = User.objects.create_user(
            email="a1@a1.ru",
            password="12345678aA!",
            first_name="Петя",
            last_name="Петин",
            phone="+79055969160",
            web_language="en",
            city="Beograd",
        )

        self.profile = BaseProfile.objects.get(web_account=self.user)
        self.client.force_authenticate(user=self.user)
        self.url = "/api/v1/auth/users/me/"

    # ------------------------------------------------------------------
    # HELPERS
    # ------------------------------------------------------------------

    def _full_payload(self, **override):
        """Фронтовый стиль — всегда пересылает все поля"""
        base = {
            "first_name": self.user.first_name,
            "last_name": self.user.last_name,
            "phone": str(self.profile.phone),
            "city": self.user.city,
        }
        base.update(override)
        return base

    def _link_whatsapp(self, username=WTS_MAIN):
        payload = self._full_payload(
            messenger_account={
                "msngr_type": "wts",
                "msngr_username": username,
            }
        )
        resp = self.client.patch(self.url, payload, format="json")
        self.assertEqual(resp.status_code, 200, resp.data)
        self.profile.refresh_from_db()
        return self.profile.messenger_account

    def _create_tg(self, subscription=True):
        ma, _ = MessengerAccount.objects.get_or_create(
            msngr_type="tm",
            msngr_id="194602954",
            msngr_username="Gatitka5",
            msngr_first_name="Natalia",
            msngr_last_name="Kirillova",
            subscription=subscription,
            city=self.user.city,
        )
        self.profile.messenger_account = ma
        self.profile.save()
        self.profile.refresh_from_db()
        logger.debug(
            "TG CREATED: BP pk=%s, MA pk=%s, BP.messenger_account_id=%s",
            self.profile.pk,
            ma.pk,
            self.profile.messenger_account_id,
        )
        return ma

    def _make_order(self, *, user=None, msngr_account=None):
        """
        Создаёт валидный заказ takeaway: Restaurant + Delivery (takeaway) + Cart + Order.
        """
        from delivery_contacts.models import Restaurant, Delivery
        from shop.models import Order

        restaurant, _ = Restaurant.objects.get_or_create(
            short_name='центр',
            defaults=dict(
                address='Milovana Milovanovića 4',
                open_time="11:00",
                close_time="22:00",
                phone="+381 61 271 4798",
                city='Beograd',
                is_active=True,
                is_default=True,
            )
        )

        delivery, _ = Delivery.objects.get_or_create(
            type='takeaway',
            city='Beograd',
            defaults=dict(
                is_active=True,
                min_time=time(11, 0),
                max_time=time(22, 0),
            )
        )

        order = Order.objects.create(
            restaurant=restaurant,
            delivery=delivery,
            source='3',
            user=user,
            msngr_account=msngr_account,
        )
        return order
    # ------------------------------------------------------------------
    # BASIC FIELDS
    # ------------------------------------------------------------------

    def test_update_first_name(self):
        payload = self._full_payload(first_name="Иван")
        resp = self.client.patch(self.url, payload, format="json")
        self.assertEqual(resp.status_code, 200)
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.first_name, "Иван")

    def test_update_last_name(self):
        payload = self._full_payload(last_name="Иванов")
        resp = self.client.patch(self.url, payload, format="json")
        self.assertEqual(resp.status_code, 200)
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.last_name, "Иванов")

    def test_update_phone(self):
        new = "+38111111111"
        payload = self._full_payload(phone=new)
        resp = self.client.patch(self.url, payload, format="json")
        self.assertEqual(resp.status_code, 200)
        self.profile.refresh_from_db()
        self.assertEqual(str(self.profile.phone), new)

    def test_update_city(self):
        payload = self._full_payload(city="Beograd")
        resp = self.client.patch(self.url, payload, format="json")
        self.assertEqual(resp.status_code, 200)
        self.user.refresh_from_db()
        self.assertEqual(self.user.city, "Beograd")

    # ------------------------------------------------------------------
    # VALIDATION ERRORS
    # ------------------------------------------------------------------

    def test_empty_first_name(self):
        payload = self._full_payload(first_name="")
        resp = self.client.patch(self.url, payload, format="json")
        self.assertEqual(resp.status_code, 400)

    def test_empty_last_name(self):
        payload = self._full_payload(last_name="")
        resp = self.client.patch(self.url, payload, format="json")
        self.assertEqual(resp.status_code, 400)

    def test_phone_cannot_be_null(self):
        payload = self._full_payload(phone=None)
        resp = self.client.patch(self.url, payload, format="json")
        self.assertEqual(resp.status_code, 400)

    # ------------------------------------------------------------------
    # WHATSAPP
    # ------------------------------------------------------------------

    def test_link_whatsapp(self):
        ma = self._link_whatsapp()
        self.assertEqual(ma.msngr_username, WTS_MAIN)
        self.assertEqual(str(ma.msngr_phone), WTS_MAIN)

    def test_unlink_whatsapp(self):
        ma = self._link_whatsapp()
        payload = self._full_payload(messenger_account={})
        resp = self.client.patch(self.url, payload, format="json")
        self.assertEqual(resp.status_code, 200)

        self.profile.refresh_from_db()
        self.assertIsNone(self.profile.messenger_account)

        ma.refresh_from_db()
        self.assertFalse(ma.registered)
        self.assertFalse(ma.subscription)

    def test_update_fields_with_existing_whatsapp(self):
        ma = self._link_whatsapp()
        old_id = ma.id

        payload = self._full_payload(
            first_name="Иван",
            last_name="Иванов",
            phone=WTS_NEW,
            city="NoviSad",
            messenger_account={
                "msngr_type": "wts",
                "msngr_username": WTS_MAIN,
            },
        )

        resp = self.client.patch(self.url, payload, format="json")
        self.assertEqual(resp.status_code, 200)

        self.profile.refresh_from_db()
        self.assertEqual(self.profile.messenger_account.id, old_id)

    # ------------------------------------------------------------------
    # TELEGRAM — NEW LINK
    # ------------------------------------------------------------------

    @override_settings(TELEGRAM_AUTH_BOTS={"Beograd": "dummy-token"})
    @mock.patch("api.serializers.check_telegram_auth")
    @mock.patch("api.serializers.get_msgr_data_validated")
    def test_link_telegram(self, mock_validate, mock_check):
        mock_validate.return_value = None
        mock_check.return_value = True

        payload = self._full_payload(
            messenger_account={
                "msngr_type": "tm",
                "id": "999001122",           # фейковый tg id
                "is_bot": False,
                "first_name": "JohnTG",
                "last_name": "DoeTG",
                "username": "johndoe_test",
                "auth_date": 1763190031,     # можно оставить такое же число, оно всё равно фейк
                "hash": "abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890",
                "city": "Beograd",
                "photo_url": "https://t.me/i/userpic/320/sample.jpg",
            },
            is_subscribed=True,
        )

        resp = self.client.patch(self.url, payload, format="json")
        # print("RESPONSE DATA:", resp.data)
        self.assertEqual(resp.status_code, 200)

        self.profile.refresh_from_db()
        ma = self.profile.messenger_account
        self.assertEqual(ma.msngr_id, "999001122")
        mock_check.assert_called_once()

    # ------------------------------------------------------------------
    # TELEGRAM — UNLINK
    # ------------------------------------------------------------------

    @override_settings(TELEGRAM_AUTH_BOTS={"Beograd": "dummy-token"})
    @mock.patch("api.serializers.check_telegram_auth")
    def test_unlink_telegram(self, mock_check):
        # print(f"\n-------{self.profile.messenger_account}")
        ma = self._create_tg()
        # print(f"\n-------{ma.msngr_id}")

        payload = self._full_payload(
            messenger_account=None
        )
        # print(f"\n-------{payload}")
        resp = self.client.patch(self.url, payload, format="json")
        # print(f"\n-------{resp}")
        self.assertEqual(resp.status_code, 200)

        self.profile.refresh_from_db()
        self.assertIsNone(self.profile.messenger_account)
        mock_check.assert_not_called()

    # ------------------------------------------------------------------
    # TELEGRAM — BASIC UPDATE WITHOUT TG FIELDS
    # ------------------------------------------------------------------

    def test_update_basic_fields_telegram_short_payload_simple(self):
        ma = self._create_tg(subscription=True)
        old_id = ma.id

        payload = self._full_payload(
            first_name="NEW",
            last_name="LAST",
            phone="+38111111118",
            city="NoviSad",
        )

        resp = self.client.patch(self.url, payload, format="json")
        self.assertEqual(resp.status_code, 200)

        self.profile.refresh_from_db()
        self.assertEqual(self.profile.messenger_account.id, old_id)

    # ------------------------------------------------------------------
    # TELEGRAM — NAMES = "" (EMPTY STRINGS)
    # ------------------------------------------------------------------

    @override_settings(TELEGRAM_AUTH_BOTS={"Beograd": "dummy-token"})
    @mock.patch("api.serializers.check_telegram_auth")
    def test_link_telegram_empty_names(self, mock_check):
        mock_check.return_value = True

        payload = self._full_payload(
            messenger_account={
                "msngr_type": "tm",
                "id": "555999777",
                "first_name": "",
                "last_name": "",
                "username": "",
                "is_bot": False,
                "auth_date": 111,
                "hash": "xyz",
                "city": "Beograd",
            }
        )

        resp = self.client.patch(self.url, payload, format="json")
        self.assertEqual(resp.status_code, 200)

        # обновим данные
        self.user.refresh_from_db()
        self.profile.refresh_from_db()

        ma = self.profile.messenger_account
        self.assertEqual(ma.msngr_first_name, "")
        self.assertEqual(ma.msngr_last_name, "")
        self.assertEqual(ma.msngr_username, "")

        # пользовательские данные не должны переписываться
        self.assertNotEqual(self.user.first_name, "")

    # ------------------------------------------------------------------
    # TELEGRAM — EMOJI / SPECIAL CHARS
    # ------------------------------------------------------------------

    @override_settings(TELEGRAM_AUTH_BOTS={"Beograd": "dummy-token"})
    @mock.patch("api.serializers.check_telegram_auth")
    def test_link_telegram_names_with_emoji(self, mock_check):
        """"""
        mock_check.return_value = True

        special = "🔥龍🐱"

        payload = self._full_payload(
            messenger_account={
                "msngr_type": "tm",
                "id": "777222111",
                "is_bot": False,
                "first_name": special,
                "last_name": special,
                "username": special,
                "auth_date": 111,
                "hash": "xyz",
                "city": "Beograd",
            }
        )

        resp = self.client.patch(self.url, payload, format="json")
        self.assertEqual(resp.status_code, 200)

        # обновим данные
        self.user.refresh_from_db()
        self.profile.refresh_from_db()

        ma = self.profile.messenger_account
        self.assertEqual(ma.msngr_first_name, special)
        self.assertEqual(ma.msngr_last_name, special)
        self.assertEqual(ma.msngr_username, special)

        # в пользователя и профиль не должны попадать символы
        self.assertNotEqual(self.user.first_name, "")
        self.assertNotEqual(self.user.last_name, "")
        self.assertNotEqual(self.profile.first_name, "")
        self.assertNotEqual(self.profile.last_name, "")

    # ------------------------------------------------------------------
    # TELEGRAM — SPECIAL SCENARIOS
    # ------------------------------------------------------------------

    def _make_ma(self, *, msngr_type="tm", msngr_id=None, username=None,
                 registered=False, profile=None):
        """Мини-хелпер для создания MessengerAccount в нужном состоянии."""
        ma = MessengerAccount.objects.create(
            msngr_type=msngr_type,
            msngr_id=str(msngr_id) if msngr_id else None,
            msngr_username=username or "",
            registered=registered,
            city=self.user.city,
            subscription=True,
        )
        if profile is not None:
            profile.messenger_account = ma
            profile.save(update_fields=["messenger_account"])
        return ma

    # ------------------------------------------------------------------
    # TELEGRAM — NEW MA HAS PROFILE, REGISTERED FALSE
    # ------------------------------------------------------------------
    @override_settings(TELEGRAM_AUTH_BOTS={"Beograd": "dummy-token"})
    @mock.patch("api.serializers.check_telegram_auth")
    @mock.patch("api.serializers.get_msgr_data_validated")
    def test_ma_scenario_1(self, mock_validate, mock_check):
        """
        bp1.messenger_account = None
        ma1.profile = bp2
        ma1.registered = False
        -> link to bp1, ma1.registered=True, bp2 cleared
        """
        mock_validate.return_value = None
        mock_check.return_value = True

        bp1 = self.profile
        bp2 = BaseProfile.objects.create(first_name="X")

        ma1 = self._make_ma(msngr_id="111", username="u1",
                            registered=False, profile=bp2)
        bp2.messenger_account = ma1
        bp2.save()

        payload = self._full_payload(
            messenger_account={"msngr_type": "tm", "id": "111"}
        )
        resp = self.client.patch(self.url, payload, format="json")
        self.assertEqual(resp.status_code, 200, resp.data)

        bp1.refresh_from_db()
        bp2.refresh_from_db()
        ma1.refresh_from_db()

        self.assertEqual(bp1.messenger_account, ma1)
        self.assertTrue(ma1.registered)
        self.assertIsNone(bp2.messenger_account)

    # ------------------------------------------------------------------
    # TELEGRAM — NEW MA HAS PROFILE, REGISTERED TRUE
    # ------------------------------------------------------------------
    @override_settings(TELEGRAM_AUTH_BOTS={"Beograd": "dummy-token"})
    @mock.patch("api.serializers.check_telegram_auth")
    @mock.patch("api.serializers.get_msgr_data_validated")
    def test_ma_scenario_2(self, mock_validate, mock_check):
        """
        bp1.messenger_account = None
        ma1.profile = bp2
        ma1.registered = True
        -> error
        """
        mock_validate.return_value = None
        mock_check.return_value = True

        bp1 = self.profile
        bp2 = BaseProfile.objects.create(first_name="Y")

        ma1 = self._make_ma(msngr_id="222", username="u2",
                            registered=True, profile=bp2)
        bp2.messenger_account = ma1
        bp2.save()

        payload = self._full_payload(
            messenger_account={"msngr_type": "tm", "id": "222"}
        )
        resp = self.client.patch(self.url, payload, format="json")
        self.assertEqual(resp.status_code, 400, resp.data)
        self.assertIn("First unlink", str(resp.data))

    # ------------------------------------------------------------------
    # TELEGRAM — BP has MA, NEW MA has PROFILE, REGISTERED FALSE
    # ------------------------------------------------------------------
    @override_settings(TELEGRAM_AUTH_BOTS={"Beograd": "dummy-token"})
    @mock.patch("api.serializers.check_telegram_auth")
    @mock.patch("api.serializers.get_msgr_data_validated")
    def test_ma_scenario_3(self, mock_validate, mock_check):
        """
        bp1.messenger_account = ma1
        ma2.profile = bp2
        ma2.registered=False
        -> bp1->ma2, ma2.registered=True,
           bp2 cleared,
           ma1.profile=None, ma1.registered=False
        """
        mock_validate.return_value = None
        mock_check.return_value = True

        bp1 = self.profile
        bp2 = BaseProfile.objects.create(first_name="Z")

        ma1 = self._make_ma(msngr_id="333", username="old_u",
                            registered=True, profile=bp1)
        bp1.messenger_account = ma1
        bp1.save()

        ma2 = self._make_ma(msngr_id="444", username="new_u",
                            registered=False, profile=bp2)
        bp2.messenger_account = ma2
        bp2.save()

        payload = self._full_payload(
            messenger_account={"msngr_type": "tm", "id": "444"}
        )

        bp1.refresh_from_db()
        bp2.refresh_from_db()
        ma1.refresh_from_db()
        ma2.refresh_from_db()

        resp = self.client.patch(self.url, payload, format="json")
        self.assertEqual(resp.status_code, 200, resp.data)

        bp1.refresh_from_db()
        bp2.refresh_from_db()
        ma1.refresh_from_db()
        ma2.refresh_from_db()

        self.assertEqual(bp1.messenger_account, ma2)
        self.assertTrue(ma2.registered)
        self.assertIsNone(bp2.messenger_account)

        self.assertFalse(
            BaseProfile.objects.filter(messenger_account=ma1).exists()
        )

        self.assertFalse(ma1.registered)
        self.assertFalse(ma1.subscription)

    # ------------------------------------------------------------------
    # TELEGRAM — BP has MA, NEW MA has PROFILE, REGISTERED TRUE
    # ------------------------------------------------------------------
    @override_settings(TELEGRAM_AUTH_BOTS={"Beograd": "dummy-token"})
    @mock.patch("api.serializers.check_telegram_auth")
    @mock.patch("api.serializers.get_msgr_data_validated")
    def test_ma_scenario_4(self, mock_validate, mock_check):
        """
        bp1.messenger_account = ma1
        ma2.profile = bp2
        ma2.registered=True
        -> error
        """
        mock_validate.return_value = None
        mock_check.return_value = True

        bp1 = self.profile
        bp2 = BaseProfile.objects.create(first_name="W")

        ma1 = self._make_ma(msngr_id="555", username="usr1",
                            registered=True, profile=bp1)
        bp1.messenger_account = ma1
        bp1.save()

        ma2 = self._make_ma(msngr_id="666", username="usr2",
                            registered=True, profile=bp2)
        bp2.messenger_account = ma2
        bp2.save()

        payload = self._full_payload(
            messenger_account={"msngr_type": "tm", "id": "666"}
        )
        resp = self.client.patch(self.url, payload, format="json")
        self.assertEqual(resp.status_code, 400, resp.data)
        self.assertIn("First unlink", str(resp.data))

    # ------------------------------------------------------------------
    # TELEGRAM — ORDERS FROM MA SHOULD BE MOVED TO BP ON LINK
    # ------------------------------------------------------------------
    @override_settings(TELEGRAM_AUTH_BOTS={"Beograd": "dummy-token"})
    @mock.patch("api.serializers.check_telegram_auth")
    @mock.patch("api.serializers.get_msgr_data_validated")
    def test_ma_orders_transferred_to_bp_on_link(self, mock_validate, mock_check):
        mock_validate.return_value = None
        mock_check.return_value = True

        bp1 = self.profile
        bp2 = BaseProfile.objects.create(first_name="WithOrdersBP")

        ma = self._make_ma(
            msngr_id="777",
            username="with_orders",
            registered=False,
            profile=bp2,
        )
        bp2.messenger_account = ma
        bp2.save()

        # создаём два заказа Telegram-аккаунта (user=None)
        o1 = self._make_order(msngr_account=ma)
        o2 = self._make_order(msngr_account=ma)

        self.assertIsNone(o1.user)
        self.assertIsNone(o2.user)

        payload = self._full_payload(
            messenger_account={"msngr_type": "tm", "id": "777"},
        )

        resp = self.client.patch(self.url, payload, format="json")
        self.assertEqual(resp.status_code, 200)

        bp1.refresh_from_db()
        o1.refresh_from_db()
        o2.refresh_from_db()
        ma.refresh_from_db()

        # MA переписан на bp1
        self.assertEqual(bp1.messenger_account, ma)

        # Заказы теперь принадлежат bp1
        self.assertEqual(o1.user, bp1)
        self.assertEqual(o2.user, bp1)

    @override_settings(TELEGRAM_AUTH_BOTS={"Beograd": "dummy-token"})
    @mock.patch("api.serializers.check_telegram_auth")
    def test_orders_remain_untouched_after_unlink_telegram(self, mock_check):
        mock_check.return_value = True

        ma = self._create_tg()  # привязан к self.profile (bp1)

        # Создаём валидные заказы, уже принадлежащие bp1
        o1 = self._make_order(user=self.profile, msngr_account=ma)
        o2 = self._make_order(user=self.profile, msngr_account=ma)

        orig_user1 = o1.user_id
        orig_user2 = o2.user_id
        orig_ma1 = o1.msngr_account_id
        orig_ma2 = o2.msngr_account_id

        resp = self.client.patch(self.url,
                                 self._full_payload(messenger_account={}),
                                 format="json")
        self.assertEqual(resp.status_code, 200)

        self.profile.refresh_from_db()

        o1.refresh_from_db()
        o2.refresh_from_db()

        # связь bp1.messenger_account удалена
        self.assertIsNone(self.profile.messenger_account)

        # но сами заказы не изменились
        self.assertEqual(o1.user_id, orig_user1)
        self.assertEqual(o2.user_id, orig_user2)
        self.assertEqual(o1.msngr_account_id, orig_ma1)
        self.assertEqual(o2.msngr_account_id, orig_ma2)

        mock_check.assert_not_called()


class PostOrderUserUpdatesTaskTests(TestCase):
    """
    Тесты на post_order_user_updates_task:
    - orders_qty / first_web_order
    - обновление имени/телефона
    - вызов адресного helper
    """

    def _make_bp(self, first_name=None, phone=None):
        bp = mock.MagicMock()
        bp.pk = 1
        bp.first_name = first_name
        bp.phone = phone
        bp.refresh_from_db = mock.MagicMock()
        bp.save = mock.MagicMock()
        bp.addresses = mock.MagicMock()
        bp.addresses.count.return_value = 0
        return bp

    def _make_order(self, bp=None, **kwargs):
        order = mock.MagicMock()
        order.id = 1
        order.user = bp
        order.source = kwargs.get("source", "1")
        order.recipient_name = kwargs.get("recipient_name", "Ivan")
        order.recipient_phone = kwargs.get("recipient_phone", "+381601234567")
        order.recipient_address = kwargs.get("recipient_address", "Pushkina 1")
        order.city = kwargs.get("city", "Beograd")
        order.coordinates = kwargs.get("coordinates", "44.8, 20.4")
        order.address_comment = kwargs.get(
            "address_comment",
            "flat:12, floor:3, interfon:45",
        )

        order.delivery = mock.MagicMock()
        order.delivery.type = kwargs.get("delivery_type", "delivery")

        order.delivery_zone = mock.MagicMock()
        order.delivery_zone.name = kwargs.get("zone_name", "Centar")

        order.msngr_account = mock.MagicMock()
        order.msngr_account.msngr_first_name = kwargs.get(
            "msngr_first_name",
            "TgName",
        )
        return order

    def _run_task(self, order, mock_addr=None):
        from users.tasks import post_order_user_updates_task

        filter_mock = mock.MagicMock()
        addr_patch = mock_addr if mock_addr is not None else mock.MagicMock()

        with mock.patch("users.tasks.Order") as MockOrder, \
             mock.patch("users.tasks.BaseProfile") as MockBaseProfile, \
             mock.patch("users.tasks._get_or_create_user_address_safe", addr_patch):

            qs = mock.MagicMock()
            qs.select_related.return_value = qs
            qs.filter.return_value = qs
            qs.first.return_value = order
            MockOrder.objects = qs

            MockBaseProfile.objects.filter.return_value = filter_mock

            post_order_user_updates_task(order_id=1)

        return filter_mock, addr_patch

    def test_task_returns_if_order_not_found(self):
        from users.tasks import post_order_user_updates_task

        with mock.patch("users.tasks.Order") as MockOrder, \
             mock.patch("users.tasks.BaseProfile") as MockBaseProfile:
            qs = mock.MagicMock()
            qs.select_related.return_value = qs
            qs.filter.return_value = qs
            qs.first.return_value = None
            MockOrder.objects = qs

            post_order_user_updates_task(order_id=999)

            MockBaseProfile.objects.filter.assert_not_called()

    def test_task_returns_if_order_has_no_user(self):
        from users.tasks import post_order_user_updates_task

        order = mock.MagicMock()
        order.user = None

        with mock.patch("users.tasks.Order") as MockOrder, \
             mock.patch("users.tasks.BaseProfile") as MockBaseProfile:
            qs = mock.MagicMock()
            qs.select_related.return_value = qs
            qs.filter.return_value = qs
            qs.first.return_value = order
            MockOrder.objects = qs

            post_order_user_updates_task(order_id=1)

            MockBaseProfile.objects.filter.assert_not_called()

    def test_orders_qty_incremented(self):
        bp = self._make_bp()
        order = self._make_order(bp, source="1")

        filter_mock, _ = self._run_task(order)

        filter_mock.update.assert_called_once()
        kwargs = filter_mock.update.call_args.kwargs
        self.assertIn("orders_qty", kwargs)

    def test_first_web_order_set_if_source_not_3(self):
        bp = self._make_bp()
        order = self._make_order(bp, source="1")

        filter_mock, _ = self._run_task(order)

        kwargs = filter_mock.update.call_args.kwargs
        self.assertIn("first_web_order", kwargs)
        self.assertTrue(kwargs["first_web_order"])

    def test_first_web_order_not_set_if_source_3(self):
        bp = self._make_bp()
        order = self._make_order(bp, source="3")

        filter_mock, _ = self._run_task(order)

        kwargs = filter_mock.update.call_args.kwargs
        self.assertNotIn("first_web_order", kwargs)

    def test_name_updated_if_empty(self):
        bp = self._make_bp(first_name="", phone="+381601111111")
        order = self._make_order(bp, source="3", recipient_name="Ivan")

        self._run_task(order)

        self.assertEqual(bp.first_name, "Ivan")
        bp.save.assert_called_once_with(update_fields=["first_name"])

    def test_name_updated_if_none(self):
        bp = self._make_bp(first_name=None, phone="+381601111111")
        order = self._make_order(bp, source="3", recipient_name="Ivan")

        self._run_task(order)

        self.assertEqual(bp.first_name, "Ivan")
        bp.save.assert_called_once_with(update_fields=["first_name"])

    def test_name_updated_if_equals_msngr_name(self):
        bp = self._make_bp(first_name="TgName", phone="+381601111111")
        order = self._make_order(
            bp,
            source="3",
            recipient_name="Ivan",
            msngr_first_name="TgName",
        )

        self._run_task(order)

        self.assertEqual(bp.first_name, "Ivan")
        bp.save.assert_called_once_with(update_fields=["first_name"])

    def test_name_not_updated_if_already_real_name(self):
        bp = self._make_bp(first_name="Petar", phone="+381601111111")
        order = self._make_order(
            bp,
            source="3",
            recipient_name="Ivan",
            msngr_first_name="TgName",
        )

        self._run_task(order)

        self.assertEqual(bp.first_name, "Petar")
        bp.save.assert_called_once_with(update_fields=["first_name"])

    def test_phone_saved_if_profile_has_no_phone(self):
        bp = self._make_bp(first_name="", phone=None)
        order = self._make_order(
            bp,
            source="3",
            recipient_name="Ivan",
            recipient_phone="+381601234567",
        )

        self._run_task(order)

        self.assertEqual(bp.first_name, "Ivan")
        self.assertEqual(bp.phone, "+381601234567")
        bp.save.assert_called_once_with(update_fields=["first_name", "phone"])

    def test_phone_not_saved_if_integrity_error_and_name_is_saved(self):
        bp = self._make_bp(first_name="", phone=None)
        bp.save.side_effect = [
            IntegrityError("users_baseprofile_phone_key"),
            None,
        ]
        order = self._make_order(
            bp,
            source="3",
            recipient_name="Ivan",
            recipient_phone="+381601234567",
        )

        self._run_task(order)

        self.assertEqual(bp.first_name, "Ivan")
        self.assertIsNone(bp.phone)
        self.assertEqual(bp.save.call_args_list[0].kwargs, {
            "update_fields": ["first_name", "phone"]
        })
        self.assertEqual(bp.save.call_args_list[1].kwargs, {
            "update_fields": ["first_name"]
        })

    def test_phone_not_updated_if_profile_already_has_phone(self):
        bp = self._make_bp(first_name="", phone="+381609999999")
        order = self._make_order(
            bp,
            source="3",
            recipient_name="Ivan",
            recipient_phone="+381601234567",
        )

        self._run_task(order)

        self.assertEqual(bp.first_name, "Ivan")
        self.assertEqual(bp.phone, "+381609999999")
        bp.save.assert_called_once_with(update_fields=["first_name"])

    def test_name_phone_block_not_executed_if_source_not_3(self):
        bp = self._make_bp(first_name="", phone=None)
        order = self._make_order(bp, source="4")

        self._run_task(order)

        bp.refresh_from_db.assert_not_called()
        bp.save.assert_not_called()

    def test_address_helper_called_for_delivery_with_valid_zone_and_slot(self):
        bp = self._make_bp(first_name="", phone=None)
        bp.addresses.count.return_value = 2
        order = self._make_order(
            bp,
            source="3",
            delivery_type="delivery",
            zone_name="Centar",
        )

        addr_mock = mock.MagicMock()
        _, addr_patch = self._run_task(order, mock_addr=addr_mock)

        addr_patch.assert_called_once_with(bp, order)

    def test_address_helper_not_called_if_zone_is_utochnit(self):
        bp = self._make_bp(first_name="", phone=None)
        bp.addresses.count.return_value = 0
        order = self._make_order(
            bp,
            source="3",
            delivery_type="delivery",
            zone_name="уточнить",
        )

        addr_mock = mock.MagicMock()
        _, addr_patch = self._run_task(order, mock_addr=addr_mock)

        addr_patch.assert_not_called()

    def test_address_helper_not_called_if_not_delivery(self):
        bp = self._make_bp(first_name="", phone=None)
        bp.addresses.count.return_value = 0
        order = self._make_order(
            bp,
            source="3",
            delivery_type="takeaway",
            zone_name="Centar",
        )

        addr_mock = mock.MagicMock()
        _, addr_patch = self._run_task(order, mock_addr=addr_mock)

        addr_patch.assert_not_called()

    def test_address_helper_not_called_if_limit_reached(self):
        bp = self._make_bp(first_name="", phone=None)
        bp.addresses.count.return_value = 3
        order = self._make_order(
            bp,
            source="3",
            delivery_type="delivery",
            zone_name="Centar",
        )

        addr_mock = mock.MagicMock()
        _, addr_patch = self._run_task(order, mock_addr=addr_mock)

        addr_patch.assert_not_called()

    def test_address_helper_called_even_if_orders_qty_update_fails(self):
        bp = self._make_bp(first_name="", phone=None)
        bp.addresses = mock.MagicMock()
        bp.addresses.count.return_value = 0

        order = self._make_order(
            bp,
            source="3",
            delivery_type="delivery",
            zone_name="Centar",
        )

        addr_mock = mock.MagicMock()

        from users.tasks import post_order_user_updates_task

        with mock.patch("users.tasks.Order") as MockOrder, \
            mock.patch("users.tasks.BaseProfile") as MockBaseProfile, \
            mock.patch("users.tasks._get_or_create_user_address_safe", addr_mock), \
            mock.patch("users.tasks.logger.exception"):

            qs = mock.MagicMock()
            qs.select_related.return_value = qs
            qs.filter.return_value = qs
            qs.first.return_value = order
            MockOrder.objects = qs

            filter_mock = mock.MagicMock()
            filter_mock.update.side_effect = Exception("orders_qty failed")
            MockBaseProfile.objects.filter.return_value = filter_mock

            post_order_user_updates_task(order_id=1)

        addr_mock.assert_called_once_with(bp, order)

    def test_address_helper_called_even_if_orders_qty_update_fails(self):
        bp = self._make_bp(first_name="", phone=None)
        bp.addresses = mock.MagicMock()
        bp.addresses.count.return_value = 0

        order = self._make_order(
            bp,
            source="3",
            delivery_type="delivery",
            zone_name="Centar",
        )

        addr_mock = mock.MagicMock()

        from users.tasks import post_order_user_updates_task

        with mock.patch("users.tasks.Order") as MockOrder, \
            mock.patch("users.tasks.BaseProfile") as MockBaseProfile, \
            mock.patch("users.tasks._get_or_create_user_address_safe", addr_mock), \
            mock.patch("users.tasks.logger.exception"):

            qs = mock.MagicMock()
            qs.select_related.return_value = qs
            qs.filter.return_value = qs
            qs.first.return_value = order
            MockOrder.objects = qs

            filter_mock = mock.MagicMock()
            filter_mock.update.side_effect = Exception("orders_qty failed")
            MockBaseProfile.objects.filter.return_value = filter_mock

            post_order_user_updates_task(order_id=1)

        addr_mock.assert_called_once_with(bp, order)


class GetOrCreateUserAddressSafeTests(TestCase):
    """
    Тесты на helper _get_or_create_user_address_safe:
    - поиск дубля по city + address + flat
    - создание нового адреса
    - пустые city/address
    - безопасное проглатывание ошибок
    """

    def _make_bp(self, addresses=None):
        bp = mock.MagicMock()
        bp.pk = 1
        bp.addresses = mock.MagicMock()
        bp.addresses.values.return_value = addresses or []
        bp.addresses.create = mock.MagicMock(return_value="created-address")
        return bp

    def _make_order(self, **kwargs):
        order = mock.MagicMock()
        order.pk = 1
        order.city = kwargs.get("city", "Beograd")
        order.recipient_address = kwargs.get("recipient_address", "Knez Mihailova 10")
        order.coordinates = kwargs.get("coordinates", "44.809,20.460")
        order.address_comment = kwargs.get(
            "address_comment",
            "flat:12, floor:3, interfon:45",
        )
        return order

    @mock.patch("delivery_contacts.utils.parse_address_comment")
    def test_returns_none_if_city_or_address_missing(self, mock_parse):
        from users.tasks import _get_or_create_user_address_safe

        bp = self._make_bp()
        order = self._make_order(city="", recipient_address="")

        result = _get_or_create_user_address_safe(bp, order)

        self.assertIsNone(result)
        bp.addresses.values.assert_not_called()
        bp.addresses.create.assert_not_called()
        mock_parse.assert_not_called()

    @mock.patch("delivery_contacts.utils.parse_address_comment")
    def test_returns_none_if_same_address_and_same_flat_exists(self, mock_parse):
        from users.tasks import _get_or_create_user_address_safe

        mock_parse.return_value = {"flat": "12", "floor": "3", "interfon": "45"}
        bp = self._make_bp(addresses=[
            {"city": "Beograd", "address": "Knez Mihailova 10", "flat": "12"},
        ])
        order = self._make_order()

        result = _get_or_create_user_address_safe(bp, order)

        self.assertIsNone(result)
        bp.addresses.create.assert_not_called()

    @mock.patch("delivery_contacts.utils.parse_address_comment")
    def test_creates_if_same_address_but_different_flat(self, mock_parse):
        from users.tasks import _get_or_create_user_address_safe

        mock_parse.return_value = {"flat": "12", "floor": "3", "interfon": "45"}
        bp = self._make_bp(addresses=[
            {"city": "Beograd", "address": "Knez Mihailova 10", "flat": "11"},
        ])
        order = self._make_order()

        result = _get_or_create_user_address_safe(bp, order)

        self.assertEqual(result, "created-address")
        bp.addresses.create.assert_called_once_with(
            city="Beograd",
            address="Knez Mihailova 10",
            coordinates="44.809,20.460",
            flat="12",
            floor="3",
            interfon="45",
        )

    @mock.patch("delivery_contacts.utils.parse_address_comment")
    def test_checks_all_existing_addresses_before_create(self, mock_parse):
        from users.tasks import _get_or_create_user_address_safe

        mock_parse.return_value = {"flat": "12", "floor": "3", "interfon": "45"}
        bp = self._make_bp(addresses=[
            {"city": "Beograd", "address": "Other 1", "flat": "1"},
            {"city": "Beograd", "address": "Knez Mihailova 10", "flat": "12"},
        ])
        order = self._make_order()

        result = _get_or_create_user_address_safe(bp, order)

        self.assertIsNone(result)
        bp.addresses.create.assert_not_called()

    @mock.patch("delivery_contacts.utils.parse_address_comment")
    def test_treats_blank_flat_and_none_flat_as_same(self, mock_parse):
        from users.tasks import _get_or_create_user_address_safe

        mock_parse.return_value = {"flat": " ", "floor": "3", "interfon": "45"}
        bp = self._make_bp(addresses=[
            {"city": "Beograd", "address": "Knez Mihailova 10", "flat": None},
        ])
        order = self._make_order()

        result = _get_or_create_user_address_safe(bp, order)

        self.assertIsNone(result)
        bp.addresses.create.assert_not_called()

    @mock.patch("users.tasks.logger.exception")
    @mock.patch("delivery_contacts.utils.parse_address_comment")
    def test_returns_none_if_create_fails(self, mock_parse, mock_logger):
        from users.tasks import _get_or_create_user_address_safe

        mock_parse.return_value = {"flat": "12", "floor": "3", "interfon": "45"}
        bp = self._make_bp(addresses=[])
        bp.addresses.create.side_effect = Exception("boom")
        order = self._make_order()

        result = _get_or_create_user_address_safe(bp, order)

        self.assertIsNone(result)
        mock_logger.assert_called_once()
