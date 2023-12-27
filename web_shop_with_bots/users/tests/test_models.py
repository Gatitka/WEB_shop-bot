from users.models import WEBAccount, BaseProfile
from django.test import TestCase
from django.db.utils import IntegrityError
from django.db.models.deletion import ProtectedError
from django.core.exceptions import ValidationError
from datetime import datetime
from django.shortcuts import get_object_or_404


class WEBAccountModelTest(TestCase):

    def setUp(self):
        self.web_account = WEBAccount.objects.create(
            first_name='Серж',
            email='test@test.ru',
            password='test@test.rutest@test.ru',
            phone="+3821452636987",
        )

    def test_instance(self):
        self.assertEqual(self.web_account.email, 'test@test.ru')
        self.assertEqual(self.web_account.id, 1)

    def test_added_date_automatically(self):
        """ Test that the date is automatically saved on creation"""
        self.assertTrue(type(self.web_account.date_joined), datetime)

    def test_is_active_false_by_default(self):
        """ Test that is_active booleans are set to false by default"""
        self.assertTrue(type(self.web_account.is_active) == bool)
        self.assertFalse(self.web_account.is_active)

    def test_str(self):
        """ Test the __str__ method"""
        expected = 'test@test.ru'
        actual = str(self.web_account)

        self.assertEqual(expected, actual)

    def test_unique_email_is_enforced(self):
        """
        Проверяем верификацию при создании пользователя на
        уникальность email.
        """
        with self.assertRaises(IntegrityError):
            web_account = WEBAccount.objects.create(
                first_name='Серж',
                email='test@test.ru',
                password='test@test.rutest@test.ru',
                phone="+3821452636986",
            )

    def test_unique_phone_is_enforced(self):
        """
        Проверяем верификацию при создании пользователя на
        уникальность номера телефона.
        """
        with self.assertRaises(Exception) as raised:
            web_account = WEBAccount.objects.create(
                first_name='Серж',
                email='test1@test1.ru',
                password='test@test.rutest@test.ru',
                phone="+3821452636987",
            )
        print(type(raised.exception))
        self.assertEqual(IntegrityError, type(raised.exception))

    def test_phone_validation_is_enforced(self):
        """
        Проверяем верификацию создания web_account - телефон.
        """
        with self.assertRaises(ValidationError):
            web_account1 = WEBAccount.objects.create(
                first_name='Серж',
                email='test1@test1.ru',
                password='test@test.rutest@test.ru',
            )

    def test_first_name_validation_is_enforced(self):
        """
        Проверяем верификацию создания web_account - имя.
        """
        with self.assertRaises(ValidationError):
            web_account1 = WEBAccount.objects.create(
                email='test1@test1.ru',
                password='test@test.rutest@test.ru',
                phone="+3821452636986",
            )

        with self.assertRaises(ValidationError):
            web_account3 = WEBAccount.objects.create(
                first_name='ja',
                email='test1@test1.ru',
                password='test@test.rutest@test.ru',
                phone="+3821452636985",
            )

    def test_base_account_created_on_web_account(self):
        """
        Проверка правильности создания base_account после создания web_account.
        """
        self.assertTrue(BaseProfile.objects.filter(
            web_account=self.web_account
            ).exists())

        base_profile = get_object_or_404(
            BaseProfile,
            web_account=self.web_account)
        self.assertEqual(base_profile.id, 1)
        self.assertEqual(base_profile.web_account_id, 1)

        self.assertEqual(self.web_account.base_profile_id, 1)

    def test_web_account_protected_if_related(self):
        """
        Проверка запрета на удаление объекта при привязке к web_account base_profile.
        """
        with self.assertRaises(ProtectedError):
            self.web_account.delete()

    def test_web_account_no_protected_if_unrelated(self):
        """
        Проверка возможности удаления пустого web_account (без привязанного base_profile.)
        """
        base_profile = get_object_or_404(
            BaseProfile,
            web_account=self.web_account)
        base_profile.web_account = None
        base_profile.save()

        self.web_account.base_profile = None
        self.web_account.save()
        self.assertTrue(self.web_account.delete())
