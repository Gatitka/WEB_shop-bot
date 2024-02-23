from datetime import datetime

from django.core.exceptions import ValidationError
from django.db.models.deletion import ProtectedError
from django.db.utils import IntegrityError
from django.shortcuts import get_object_or_404
from django.test import TestCase
from django.contrib.auth import get_user_model

from users.models import BaseProfile

User = get_user_model()


class WEBAccountModelTest(TestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.web_account_create_edit = User.objects.create(
            first_name='Серж',
            last_name='Вахин',
            email='test@test.ru',
            password='testpassword',  # Передайте значение пароля здесь
            phone="+381612714798",
        )

        cls.web_account_linkdelete = User.objects.create(
            first_name='Серж',
            last_name='Вахин',
            email='fest@fest.ru',
            password='testpassword',  # Передайте значение пароля здесь
            phone="+381612714790",
        )

        cls.web_account_str = User.objects.create(
            first_name='Серж',
            last_name='Вахин',
            email='vest@vest.ru',
            password='testpassword',  # Передайте значение пароля здесь
            phone="+381612714791",
        )

    def test_web_account_str_representation(self):
        """ Test the __str__ method of web account """
        expected = 'vest@vest.ru'
        actual = str(WEBAccountModelTest.web_account_str)
        self.assertEqual(expected, actual)

    def test_first_name_not_empty(self):
        """ Test that first name cannot be empty """
        self.assertIsNotNone(WEBAccountModelTest.web_account_create_edit.first_name)

    def test_last_name_not_empty(self):
        """ Test that last name cannot be empty """
        self.assertIsNotNone(WEBAccountModelTest.web_account_create_edit.last_name)

    def test_email_not_empty(self):
        """ Test that email cannot be empty """
        self.assertIsNotNone(WEBAccountModelTest.web_account_create_edit.email)

    def test_phone_not_empty(self):
        """ Test that phone cannot be empty """
        self.assertIsNotNone(WEBAccountModelTest.web_account_create_edit.phone)

    def test_web_account_created_with_inactive_status(self):
        """ Test that web account is created with inactive status """
        self.assertFalse(WEBAccountModelTest.web_account_create_edit.is_active)



    def test_clean_method_validates_first_name(self):
        """ Test that clean method validates first name """
        WEBAccountModelTest.web_account_create_edit.first_name = ''
        with self.assertRaises(ValidationError):
            WEBAccountModelTest.web_account_create_edit.clean()

    def test_clean_method_validates_first_name_content(self):
        """ Test that clean method validates first name """
        WEBAccountModelTest.web_account_create_edit.first_name = 'ja'
        with self.assertRaises(ValidationError):
            WEBAccountModelTest.web_account_create_edit.clean()

    def test_clean_method_validates_last_name(self):
        """ Test that clean method validates last name """
        WEBAccountModelTest.web_account_create_edit.last_name = ''
        with self.assertRaises(ValidationError):
            WEBAccountModelTest.web_account_create_edit.clean()

    def test_clean_method_validates_email(self):
        """ Test that clean method validates email """
        WEBAccountModelTest.web_account_create_edit.email = ''
        with self.assertRaises(ValidationError):
            WEBAccountModelTest.web_account_create_edit.clean()

    def test_clean_method_validates_phone(self):
        """ Test that clean method validates phone """
        WEBAccountModelTest.web_account_create_edit.phone = ''
        with self.assertRaises(ValidationError):
            WEBAccountModelTest.web_account_create_edit.clean()

    def test_instance(self):
        self.assertEqual(WEBAccountModelTest.web_account_create_edit.pk, 1)

    def test_added_date_automatically(self):
        """ Test that the date is automatically saved on creation"""
        self.assertTrue(
            type(WEBAccountModelTest.web_account_create_edit.date_joined),
            datetime
        )

    def test_is_active_false_by_default(self):
        """ Test that is_active booleans are set to false by default"""
        self.assertTrue(
            type(WEBAccountModelTest.web_account_create_edit.is_active) is bool
        )
        self.assertFalse(WEBAccountModelTest.web_account_create_edit.is_active)

    def test_unique_email_is_enforced(self):
        """
        Проверяем верификацию при создании пользователя на
        уникальность email.
        """
        with self.assertRaises(Exception) as raised:
            web_account1 = User.objects.create(
                first_name='Сер',
                last_name='Вахи',
                email='test@test.ru',
                password='test@test.rutest@test.ru',
                phone="+381612714797",
            )
        self.assertEqual(ValidationError, type(raised.exception))

    def test_unique_phone_is_enforced(self):
        """
        Проверяем верификацию при создании пользователя на
        уникальность номера телефона.
        """
        with self.assertRaises(Exception) as raised:
            web_account1 = User.objects.create(
                first_name='Сер',
                last_name='Вахи',
                email='test1@test.ru',
                password='test@test.rutest@test.ru',
                phone="+381612714798",
            )
        self.assertEqual(ValidationError, type(raised.exception))

    def test_phone_validation_is_enforced(self):
        """
        Проверяем верификацию создания web_account - телефон.
        """
        with self.assertRaises(Exception) as raised:
            web_account1 = User.objects.create(
                    first_name='Серж',
                    last_name='Вахин',
                    email='test7@test.ru',
                    password='test@test.rutest@test.ru',
                )
        self.assertEqual(ValidationError, type(raised.exception))

    def test_first_name_validation_is_enforced(self):
        """
        Проверяем верификацию создания web_account - имя.
        """
        with self.assertRaises(Exception) as raised:
            web_account1 = User.objects.create(
                last_name='Вахин',
                email='te8st@test.ru',
                password='test@test.rutest@test.ru',
                phone="+381612714797"
            )
        self.assertEqual(ValidationError, type(raised.exception))

    def test_base_account_created_on_web_account(self):
        """
        Проверка правильности создания base_account после создания web_account.
        """
        self.assertTrue(BaseProfile.objects.filter(
            web_account=WEBAccountModelTest.web_account_linkdelete
            ).exists())

        base_profile = BaseProfile.objects.get(
            web_account=WEBAccountModelTest.web_account_linkdelete)
        self.assertEqual(base_profile.id, 2)
        self.assertEqual(
            WEBAccountModelTest.web_account_linkdelete.base_profile.id,
            2)

    def test_web_account_protected_if_related(self):
        """
        Проверка запрета на удаление объекта при привязке к web_account
        base_profile.
        """
        with self.assertRaises(Exception) as raised:
            WEBAccountModelTest.web_account_create_edit.delete()
        self.assertEqual(ProtectedError, type(raised.exception))

    def test_web_account_no_protected_if_unrelated(self):
        """
        Проверка возможности удаления пустого web_account
        (без привязанного base_profile.)
        """
        base_profile = BaseProfile.objects.get(
            web_account=WEBAccountModelTest.web_account_linkdelete)
        base_profile.web_account = None
        base_profile.save(update_fields=['web_account'])

        self.assertTrue(WEBAccountModelTest.web_account_linkdelete.delete())
