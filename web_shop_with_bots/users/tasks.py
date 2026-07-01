import logging

from celery import shared_task
from django.db import IntegrityError
from django.db.models import F, Value
from django.db.models.functions import Coalesce
from django.db.utils import OperationalError
from django.utils import timezone
from rest_framework_simplejwt.token_blacklist import models

from shop.models import Order
from users.models import BaseProfile

logger = logging.getLogger(__name__)


# ---------------- ПОСЛЕ РАЗМЕЩЕНИЯ ЗАКАЗА ОБНОВИТЬ ДАННЫЕ КЛИЕНТА ----------------

@shared_task(
    queue="orders",
    bind=True,
    autoretry_for=(OperationalError,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 2},
)
def post_order_user_updates_task(self, order_id: int) -> None:
    """
    Best-effort апдейты пользователя после успешного создания заказа:
    - orders_qty +1
    - first_web_order=True для web-заказов
    - если source == '3' -> проверяем и обновляем имя/телефон
    - если доставка и зона ok -> сохраняем адрес

    Ничего в этой таске не должно ронять создание заказа.
    """
    task_id = getattr(getattr(self, "request", None), "id", None)
    logger.info(
        "post_order_user_updates_task started task_id=%s order_id=%s",
        task_id,
        order_id,
    )

    order = (
        Order.objects
        .select_related("user", "msngr_account", "delivery", "delivery_zone")
        .filter(id=order_id)
        .first()
    )

    if not order:
        logger.warning(
            "post_order_user_updates_task order_not_found order_id=%s",
            order_id,
        )
        return

    if not order.user:
        logger.warning(
            "post_order_user_updates_task skipped_no_user order_id=%s source=%r msngr_account_id=%s recipient_phone=%r",
            order_id,
            getattr(order, "source", None),
            getattr(order, "msngr_account_id", None),
            getattr(order, "recipient_phone", None),
        )
        return

    bp = order.user
    bp_id = bp.pk
    source = str(getattr(order, "source", ""))
    delivery_type = getattr(getattr(order, "delivery", None), "type", None)
    delivery_zone = getattr(getattr(order, "delivery_zone", None), "name", None)

    logger.debug(
        "post_order_user_updates_task context order_id=%s bp_id=%s source=%r delivery_type=%r delivery_zone=%r recipient_name=%r recipient_phone=%r city=%r address=%r msngr_account_id=%s",
        order_id,
        bp_id,
        source,
        delivery_type,
        delivery_zone,
        getattr(order, "recipient_name", None),
        getattr(order, "recipient_phone", None),
        getattr(order, "city", None),
        getattr(order, "recipient_address", None),
        getattr(order, "msngr_account_id", None),
    )

    # 1) orders_qty / first_web_order
    try:
        before = BaseProfile.objects.filter(pk=bp_id).values(
            "orders_qty", "first_web_order"
        ).first()

        update_kwargs = {"orders_qty": Coalesce(F("orders_qty"), Value(0)) + 1}
        if source != "3":
            update_kwargs["first_web_order"] = True

        updated_rows = BaseProfile.objects.filter(pk=bp_id).update(
            **update_kwargs)
        after = BaseProfile.objects.filter(pk=bp_id).values(
            "orders_qty", "first_web_order"
        ).first()

        logger.info(
            "post_order_user_updates_task orders_updated order_id=%s bp_id=%s updated_rows=%s before=%s after=%s",
            order_id,
            bp_id,
            updated_rows,
            before,
            after,
        )
    except Exception:
        logger.exception(
            "post_order_user_updates_task orders_update_failed order_id=%s bp_id=%s source=%r",
            order_id,
            bp_id,
            source,
        )

    # 2) имя / телефон только для bot orders
    if source == "3":
        bp.refresh_from_db(fields=["first_name", "phone"])
        try:
            _update_bot_profile_fields(bp=bp, order=order)
        except Exception:
            logger.exception(
                "post_order_user_updates_task profile_update_failed order_id=%s bp_id=%s recipient_name=%r recipient_phone=%r current_first_name=%r current_phone=%r",
                order_id,
                bp_id,
                getattr(order, "recipient_name", None),
                getattr(order, "recipient_phone", None),
                getattr(bp, "first_name", None),
                getattr(bp, "phone", None),
            )
    else:
        logger.debug(
            "post_order_user_updates_task profile_branch_skipped_non_bot order_id=%s bp_id=%s source=%r",
            order_id,
            bp_id,
            source,
        )

    # 3) адрес
    can_process_address = bool(
        order.delivery
        and order.delivery.type == "delivery"
        and order.delivery_zone
        and order.delivery_zone.name != "уточнить"
    )

    addresses_count = bp.addresses.count()
    logger.debug(
        "post_order_user_updates_task address_check order_id=%s bp_id=%s can_process=%s delivery_type=%r delivery_zone=%r addresses_count=%s",
        order_id,
        bp_id,
        can_process_address,
        delivery_type,
        delivery_zone,
        addresses_count,
    )

    if not can_process_address:
        logger.debug(
            "post_order_user_updates_task address_skipped order_id=%s bp_id=%s reason=branch_condition",
            order_id,
            bp_id,
        )
        logger.info(
            "post_order_user_updates_task finished order_id=%s bp_id=%s",
            order_id,
            bp_id,
        )
        return

    if addresses_count >= 3:
        logger.info(
            "post_order_user_updates_task address_skipped order_id=%s bp_id=%s reason=max_addresses_reached addresses_count=%s",
            order_id,
            bp_id,
            addresses_count,
        )
        logger.info(
            "post_order_user_updates_task finished order_id=%s bp_id=%s",
            order_id,
            bp_id,
        )
        return

    try:
        address_obj = _get_or_create_user_address_safe(bp, order)
        if address_obj is not None:
            logger.info(
                "post_order_user_updates_task address_created order_id=%s bp_id=%s address_id=%s city=%r address=%r",
                order_id,
                bp_id,
                address_obj.pk,
                getattr(order, "city", None),
                getattr(order, "recipient_address", None),
            )
        else:
            logger.debug(
                "post_order_user_updates_task address_not_created order_id=%s bp_id=%s reason=duplicate_or_incomplete_data",
                order_id,
                bp_id,
            )
    except Exception:
        logger.exception(
            "post_order_user_updates_task address_update_failed order_id=%s bp_id=%s city=%r address=%r",
            order_id,
            bp_id,
            getattr(order, "city", None),
            getattr(order, "recipient_address", None),
        )

    logger.info(
        "post_order_user_updates_task finished order_id=%s bp_id=%s",
        order_id,
        bp_id,
    )


def _clean_name(value):
    if value is None:
        return None
    value = str(value).strip()
    return value or None


def _update_bot_profile_fields(*, bp, order) -> None:
    order_id = getattr(order, "id", None)
    bp_id = getattr(bp, "pk", None)

    msngr_first = _clean_name(getattr(order.msngr_account, "msngr_first_name", None))
    current_first_name = _clean_name(bp.first_name)
    new_first_name = _clean_name(getattr(order, "recipient_name", None))
    current_phone = bp.phone
    new_phone = getattr(order, "recipient_phone", None)

    logger.debug(
        "_update_bot_profile_fields start order_id=%s bp_id=%s current_first_name=%r msngr_first=%r current_phone=%r new_first_name=%r new_phone=%r",
        order_id,
        bp_id,
        current_first_name,
        msngr_first,
        current_phone,
        new_first_name,
        new_phone,
    )

    update_fields = []

    # Имя разрешено переписать только если оно пустое либо совпадает с именем в мессенджере.
    can_override_name = current_first_name in [None, msngr_first]

    if not new_first_name:
        logger.debug(
            "_update_bot_profile_fields first_name_skipped order_id=%s bp_id=%s reason=empty_new_name",
            order_id,
            bp_id,
        )
    elif not can_override_name:
        logger.debug(
            "_update_bot_profile_fields first_name_skipped order_id=%s bp_id=%s reason=protected current_first_name=%r msngr_first=%r",
            order_id,
            bp_id,
            current_first_name,
            msngr_first,
        )
    elif current_first_name == new_first_name:
        logger.debug(
            "_update_bot_profile_fields first_name_skipped order_id=%s bp_id=%s reason=same_value value=%r",
            order_id,
            bp_id,
            current_first_name,
        )
    else:
        bp.first_name = new_first_name
        update_fields.append("first_name")
        logger.info(
            "_update_bot_profile_fields first_name_changed order_id=%s bp_id=%s old=%r new=%r",
            order_id,
            bp_id,
            current_first_name,
            new_first_name,
        )

    # Телефон ставим только если он ещё не задан в профиле.
    if not new_phone:
        logger.debug(
            "_update_bot_profile_fields phone_skipped order_id=%s bp_id=%s reason=empty_new_phone",
            order_id,
            bp_id,
        )
    elif current_phone is not None:
        logger.debug(
            "_update_bot_profile_fields phone_skipped order_id=%s bp_id=%s reason=already_set current_phone=%r",
            order_id,
            bp_id,
            current_phone,
        )
    else:
        bp.phone = new_phone
        update_fields.append("phone")
        logger.info(
            "_update_bot_profile_fields phone_changed order_id=%s bp_id=%s old=%r new=%r",
            order_id,
            bp_id,
            current_phone,
            new_phone,
        )

    if not update_fields:
        logger.debug(
            "_update_bot_profile_fields no_changes order_id=%s bp_id=%s",
            order_id,
            bp_id,
        )
        return

    try:
        bp.save(update_fields=update_fields)
        logger.info(
            "_update_bot_profile_fields saved order_id=%s bp_id=%s fields=%s final_first_name=%r final_phone=%r",
            order_id,
            bp_id,
            update_fields,
            bp.first_name,
            bp.phone,
        )
    except IntegrityError as exc:
        if "phone" in update_fields and "users_baseprofile_phone_key" in str(exc):
            logger.warning(
                "_update_bot_profile_fields phone_conflict order_id=%s bp_id=%s phone=%r",
                order_id,
                bp_id,
                new_phone,
            )
            bp.phone = None
            if "first_name" in update_fields:
                bp.save(update_fields=["first_name"])
                logger.info(
                    "_update_bot_profile_fields saved_without_phone order_id=%s bp_id=%s final_first_name=%r",
                    order_id,
                    bp_id,
                    bp.first_name,
                )
            return
        raise


def _normalize_address_part(value):
    if value is None:
        return None
    value = str(value).strip()
    return value or None


def _address_key(city, address, flat):
    return (
        (city or "").strip(),
        (address or "").strip(),
        _normalize_address_part(flat),
    )


def _get_or_create_user_address_safe(base_profile, order):
    """
    Берём первый дубль, если есть; иначе создаём.
    Не используем get()/get_or_create(), чтобы не ловить MultipleObjectsReturned.
    """
    from delivery_contacts.utils import parse_address_comment

    bp_id = getattr(base_profile, "pk", None)
    order_id = getattr(order, "id", None)
    city = (order.city or "").strip()
    address = (order.recipient_address or "").strip()

    if not city or not address:
        logger.debug(
            "_get_or_create_user_address_safe skipped order_id=%s bp_id=%s reason=empty_city_or_address city=%r address=%r",
            order_id,
            bp_id,
            city,
            address,
        )
        return None

    try:
        address_parts = parse_address_comment(order.address_comment or "")
        flat = _normalize_address_part(address_parts.get("flat"))
        floor = _normalize_address_part(address_parts.get("floor"))
        interfon = _normalize_address_part(address_parts.get("interfon"))

        new_key = _address_key(city, address, flat)
        existing_addresses = list(
            base_profile.addresses.values("id", "city", "address", "flat")
        )

        logger.debug(
            "_get_or_create_user_address_safe parsed order_id=%s bp_id=%s new_key=%r existing_addresses=%s",
            order_id,
            bp_id,
            new_key,
            existing_addresses,
        )

        for item in existing_addresses:
            existing_key = _address_key(item["city"], item["address"], item["flat"])
            if existing_key == new_key:
                logger.debug(
                    "_get_or_create_user_address_safe duplicate order_id=%s bp_id=%s existing_address_id=%s existing_key=%r",
                    order_id,
                    bp_id,
                    item["id"],
                    existing_key,
                )
                return None

        address_obj = base_profile.addresses.create(
            city=city,
            address=address,
            coordinates=order.coordinates,
            flat=flat,
            floor=floor,
            interfon=interfon,
        )
        return address_obj

    except Exception:
        logger.exception(
            "_get_or_create_user_address_safe failed order_id=%s bp_id=%s city=%r address=%r",
            order_id,
            bp_id,
            city,
            address,
        )
        return None


# -------------- УДАЛИТЬ СТАРЫЕ ТОКЕНЫ -------------------

@shared_task
def delete_expired_tokens():
    delete_exp_blcklist_tokens()
    delete_exp_outstd_tokens()
    logger.info("expired_tokens_deleted")


def delete_exp_blcklist_tokens():
    expired_blck_tokens = models.BlacklistedToken.objects.filter(
        token__expires_at__lt=timezone.now()
    )
    for blcklist_token in expired_blck_tokens:
        outst_token = blcklist_token.token
        blcklist_token.delete()
        outst_token.delete()
    logger.info("expired_blacklisted_tokens_deleted")


def delete_exp_outstd_tokens():
    expired_outstd_tokens = models.OutstandingToken.objects.filter(
        expires_at__lt=timezone.now()
    )
    expired_outstd_tokens.delete()
    logger.info("expired_outstanding_tokens_deleted")
