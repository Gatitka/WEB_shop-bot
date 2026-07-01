# Тесты для `post_order_user_updates_task`

## Что это и зачем

`post_order_user_updates_task` — Celery-таска которая запускается после создания заказа и обновляет данные клиента:
- увеличивает счётчик заказов (`orders_qty + 1`)
- выставляет флаг `first_web_order` если заказ не из Telegram
- обновляет имя и телефон клиента (только если заказ из Telegram, `source == '3'`)
- сохраняет адрес доставки в профиль клиента

Таска работает в режиме **best-effort** — если что-то пошло не так, она логирует ошибку и продолжает. Создание заказа никогда не должно падать из-за этой таски.

---

## Почему используем моки, а не реальную БД

Таска зависит от многих моделей: `Order`, `BaseProfile`, `UserAddress`, `MessengerAccount`, `Delivery`, `DeliveryZone`. Создавать все эти объекты в тестовой БД — долго и сложно.

Вместо этого мы мокаем (`mock.MagicMock`) только те объекты которые нужны, и проверяем что таска делает правильные вызовы.

**Важный нюанс:** в `users/tasks.py` есть импорты на верхнем уровне файла:
```python
from shop.models import Order
from users.models import BaseProfile
```

Чтобы патч сработал, нужно патчить именно эти имена в модуле `users.tasks`:
```python
mock.patch("users.tasks.Order")
mock.patch("users.tasks.BaseProfile")
```

Если внутри функции есть дублирующие локальные импорты — они перезаписывают патч и тесты не работают. Локальные импорты внутри функции нужно удалять.

---

## Структура тестов

### Хелперы

**`_make_bp(first_name, phone)`** — создаёт мок `BaseProfile`.
`refresh_from_db` замокан как no-op чтобы не сбрасывал значения которые мы задали.

**`_make_order(bp, **kwargs)`** — создаёт мок заказа со всеми нужными полями.
Принимает `bp` (профиль клиента) и параметры через `kwargs`:

| Параметр | По умолчанию | Что это |
|---|---|---|
| `source` | `"1"` | источник заказа, `"3"` = Telegram |
| `recipient_name` | `"Ivan"` | имя получателя |
| `recipient_phone` | `"+381601234567"` | телефон получателя |
| `delivery_type` | `"delivery"` | тип доставки |
| `zone_name` | `"Centar"` | название зоны доставки |
| `msngr_first_name` | `"TgName"` | имя в Telegram-аккаунте |

**`_run_task(order, mock_addr)`** — запускает таску с замоканными зависимостями.
Возвращает `(filter_mock, addr_patch)`:
- `filter_mock` — мок `BaseProfile.objects.filter()`, проверяем через него вызовы `.update()`
- `addr_patch` — мок функции `_get_or_create_user_address_safe`, проверяем была ли вызвана

---

## Что покрывают тесты

### 1. Верхнеуровневые тесты `PostOrderUserUpdatesTaskTests`

| Тест | Что проверяет |
|---|---|
| `test_task_returns_if_order_not_found` | таска не падает если заказ не найден |
| `test_task_returns_if_order_has_no_user` | таска не падает если у заказа нет пользователя |
| `test_orders_qty_incremented` | `orders_qty` увеличивается на 1 |
| `test_first_web_order_set_if_source_not_3` | `first_web_order=True` если `source != '3'` |
| `test_first_web_order_not_set_if_source_3` | `first_web_order` не трогается если `source == '3'` |
| `test_name_updated_if_empty` | имя обновляется если оно пустая строка |
| `test_name_updated_if_none` | имя обновляется если оно `None` |
| `test_name_updated_if_equals_msngr_name` | имя обновляется если совпадает с именем в Telegram |
| `test_name_not_updated_if_already_real_name` | имя не меняется если уже заполнено нормальным значением |
| `test_phone_saved_if_profile_has_no_phone` | телефон сохраняется если у профиля его нет |
| `test_phone_not_saved_if_integrity_error_and_name_is_saved` | если телефон не сохранился из-за unique-конфликта, имя всё равно сохраняется |
| `test_phone_not_updated_if_profile_already_has_phone` | существующий телефон не перезаписывается |
| `test_name_phone_block_not_executed_if_source_not_3` | имя/телефон не обновляются для не-Telegram заказа |
| `test_address_helper_called_for_delivery_with_valid_zone_and_slot` | helper адреса вызывается для delivery-заказа с валидной зоной и свободным слотом |
| `test_address_helper_not_called_if_zone_is_utochnit` | helper адреса не вызывается если зона `"уточнить"` |
| `test_address_helper_not_called_if_not_delivery` | helper адреса не вызывается для самовывоза |
| `test_address_helper_not_called_if_limit_reached` | helper адреса не вызывается если у клиента уже 3 адреса |
### 1. Верхнеуровневые тесты `PostOrderUserUpdatesTaskTests`

| Тест | Что проверяет |
|---|---|
| `test_task_returns_if_order_not_found` | таска не падает если заказ не найден |
| `test_task_returns_if_order_has_no_user` | таска не падает если у заказа нет пользователя |
| `test_orders_qty_incremented` | `orders_qty` увеличивается на 1 |
| `test_first_web_order_set_if_source_not_3` | `first_web_order=True` если `source != '3'` |
| `test_first_web_order_not_set_if_source_3` | `first_web_order` не трогается если `source == '3'` |
| `test_name_updated_if_empty` | имя обновляется если оно пустая строка |
| `test_name_updated_if_none` | имя обновляется если оно `None` |
| `test_name_updated_if_equals_msngr_name` | имя обновляется если совпадает с именем в Telegram |
| `test_name_not_updated_if_already_real_name` | имя не меняется если уже заполнено нормальным значением |
| `test_phone_saved_if_profile_has_no_phone` | телефон сохраняется если у профиля его нет |
| `test_phone_not_saved_if_integrity_error_and_name_is_saved` | если телефон не сохранился из-за unique-конфликта, имя всё равно сохраняется |
| `test_phone_not_updated_if_profile_already_has_phone` | существующий телефон не перезаписывается |
| `test_name_phone_block_not_executed_if_source_not_3` | имя/телефон не обновляются для не-Telegram заказа |
| `test_address_helper_called_for_delivery_with_valid_zone_and_slot` | helper адреса вызывается для delivery-заказа с валидной зоной и свободным слотом |
| `test_address_helper_not_called_if_zone_is_utochnit` | helper адреса не вызывается если зона `"уточнить"` |
| `test_address_helper_not_called_if_not_delivery` | helper адреса не вызывается для самовывоза |
| `test_address_helper_not_called_if_limit_reached` | helper адреса не вызывается если у клиента уже 3 адреса |
| `test_address_helper_called_even_if_orders_qty_update_fails` | даже если падает обновление `orders_qty/first_web_order`, адрес всё равно обрабатывается |
| `test_address_helper_called_even_if_name_phone_block_fails` | даже если падает блок имени/телефона, адрес всё равно обрабатывается |


---

### 2. Тесты helper-функции `_get_or_create_user_address_safe`

Это отдельный набор тестов на внутреннюю логику сохранения адреса.
Они нужны потому, что адресная логика уже вынесена в helper и её удобнее проверять отдельно от всей таски.

| Тест | Что проверяет |
|---|---|
| `test_returns_none_if_city_or_address_missing` | если `city` или `recipient_address` пустые — адрес не создаётся |
| `test_returns_none_if_same_address_and_same_flat_exists` | дубль по `city + address + flat` не создаётся |
| `test_creates_if_same_address_but_different_flat` | если адрес тот же, но квартира другая — создаётся новый адрес |
| `test_checks_all_existing_addresses_before_create` | helper проверяет **все** адреса, а не только первый; ловит баг с преждевременным `create()` внутри цикла |
| `test_treats_blank_flat_and_none_flat_as_same` | `flat=None` и `flat=""` считаются одним и тем же значением |
| `test_returns_none_if_create_fails` | если `create()` упал, helper не роняет процесс и возвращает `None` |

---

## Почему адресные тесты вынесены в отдельный класс

Верхнеуровневые тесты `PostOrderUserUpdatesTaskTests` проверяют orchestration:
- когда таска должна обновлять имя/телефон,
- когда должна вызывать helper адреса,
- когда не должна вызывать его вообще.

Но они **не проверяют внутреннюю логику сравнения адресов**.

Поэтому адресные кейсы лучше держать отдельно в классе
`GetOrCreateUserAddressSafeTests`, где проще изолированно проверить:

- сравнение по `city + address + flat`
- поведение при пустых данных
- поведение при ошибке `create()`
- корректный проход по всему списку адресов пользователя

---

## Как запускать

```bash
# только верхнеуровневые тесты таски
python manage.py test users.tests.PostOrderUserUpdatesTaskTests

# только тесты helper-а адресов
python manage.py test users.tests.GetOrCreateUserAddressSafeTests

# один конкретный тест
python manage.py test users.tests.GetOrCreateUserAddressSafeTests.test_checks_all_existing_addresses_before_create


---

## Как добавить новый тест

1. Создай профиль и заказ через хелперы:
```python
def test_my_new_case(self):
    bp = self._make_bp(first_name="", phone=None)
    order = self._make_order(bp, source="3", recipient_name="Anna")
```

2. Если нужно проверить адрес — передай `mock_addr`:
```python
    mock_addr = mock.MagicMock()
    self._run_task(order, mock_addr=mock_addr)
    mock_addr.assert_called_once_with(bp, order)
```

3. Если нужно проверить `orders_qty` или `first_web_order` — используй `filter_mock`:
```python
    filter_mock, _ = self._run_task(order)
    call_kwargs = filter_mock.update.call_args.kwargs
    self.assertIn("orders_qty", call_kwargs)
```

4. Если нужно проверить имя или телефон — просто смотри на `bp` после вызова:
```python
    self._run_task(order)
    self.assertEqual(bp.first_name, "Anna")
```
