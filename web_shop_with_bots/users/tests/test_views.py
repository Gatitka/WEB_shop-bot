from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from users.models import BaseProfile, UserAddress

User = get_user_model()


class TestUserViews(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create(
            email='test@example.com',
            first_name='John',
            last_name='Doe',
            phone='+381640000000'
        )
        self.client.force_authenticate(user=self.user)

    def test_delete_user_in_djoser_is_blocked(self):
        response = self.client.delete(reverse('api:users'))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_deleted)

    def test_my_addresses_list(self):
        response = self.client.get(reverse('api:user_addresses-list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_create_user_address(self):
        data = {'address': '123 Main St'}
        response = self.client.post(reverse('api:user_addresses-list'), data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(UserAddress.objects.filter(
            address='123 Main St').exists())

    def test_update_user_address(self):
        user_address = UserAddress.objects.create(
            address='456 Elm St',
            base_profile=self.user.base_profile)
        data = {'address': '789 Oak St'}
        response = self.client.put(reverse(
            'api:user_addresses-detail',
            kwargs={'pk': user_address.pk}), data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        user_address.refresh_from_db()
        self.assertEqual(user_address.address, '789 Oak St')

    def test_delete_user_address(self):
        user_address = UserAddress.objects.create(
            address='456 Elm St',
            base_profile=self.user.base_profile)
        response = self.client.delete(reverse('api:user_addresses-detail',
                                              kwargs={'pk': user_address.pk}))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(UserAddress.objects.filter(pk=user_address.pk).exists())
