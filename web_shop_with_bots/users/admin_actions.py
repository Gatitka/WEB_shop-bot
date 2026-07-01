from django.db import transaction
from django.contrib import messages

from rest_framework_simplejwt.token_blacklist.models import (
    OutstandingToken,
    BlacklistedToken,
)

from users.models import BaseProfile, WEBAccount, UserAddress
from shop.models import Order
from audit.models import AuditLog
from tm_bot.models import MessengerAccount, MessengerAccountBot
from promos.models import CampaignOpenEvent


def _total_delete_single_base_profile(base_profile: BaseProfile) -> None:
    """
    Полное удаление одного клиента и всего, что с ним связано.
    """

    # 1. WEBAccount + AuditLog + JWT токены
    web_account: WEBAccount | None = base_profile.web_account
    if web_account:
        # 1.1 AuditLog по web_account и base_profile
        AuditLog.objects.filter(user=web_account).delete()
        AuditLog.objects.filter(base_profile=base_profile).delete()

        # 1.2 JWT токены: сначала blacklist, потом сами токены
        BlacklistedToken.objects.filter(token__user=web_account).delete()
        OutstandingToken.objects.filter(user=web_account).delete()

        # отцепляем web_account от BaseProfile (из-за PROTECT)
        base_profile.web_account = None
        base_profile.save(update_fields=["web_account"])

        # 1.3 удаляем WEBAccount
        web_account.delete()

    # 2. Заказы (OrderDish уйдут каскадом от Order)
    Order.objects.filter(user=base_profile).delete()

    # 3. Адреса клиента
    # сначала убираем ссылку my_addresses (on_delete=PROTECT),
    # потом удаляем все UserAddress этого base_profile
    if base_profile.my_addresses_id:
        base_profile.my_addresses = None
        base_profile.save(update_fields=["my_addresses"])

    UserAddress.objects.filter(base_profile=base_profile).delete()

    # 4. MessengerAccount и связанные сущности
    messenger_account: MessengerAccount | None = base_profile.messenger_account
    if messenger_account:
        # 4.1 CampaignOpenEvent по этому MessengerAccount
        CampaignOpenEvent.objects.filter(user=messenger_account).delete()

        # 4.2 MessengerAccountBot по этому MessengerAccount
        MessengerAccountBot.objects.filter(
            messenger_account=messenger_account
        ).delete()

        # отцепляем MA от BaseProfile (OneToOne SET_NULL)
        base_profile.messenger_account = None
        base_profile.save(update_fields=["messenger_account"])

        # 4.3 удаляем MessengerAccount
        messenger_account.delete()

    # 5. Удаляем сам BaseProfile
    base_profile.delete()


def total_user_delete(modeladmin, request, queryset):
    """
    Полное удаление пользователя, всех аккаунтов и всего, что с ним связано.
    В заказах просто стираем привязки (через удаление Order'ов для user).
    """
    deleted_count = 0

    # подгружаем связанные аккаунты, чтобы не было лишних запросов
    queryset = queryset.select_related("web_account", "messenger_account")

    for base_profile in queryset:
        with transaction.atomic():
            _total_delete_single_base_profile(base_profile)
        deleted_count += 1

    messages.success(
        request,
        f"Полностью удалено клиентов: {deleted_count}",
    )


total_user_delete.short_description = "Полное удаление аккаунта и связей"
