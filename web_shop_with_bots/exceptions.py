class NoDeliveryDataException(Exception):
    """The requested model field does not exist"""
    pass


class BotOrderSaveError(Exception):
    """Исключение для ошибки сохранения заказа в боте."""
    pass


class BotMessageSendError(Exception):
    """Исключение для ошибки отправки сообщения в боте."""
    pass
