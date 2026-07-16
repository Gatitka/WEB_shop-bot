from django.utils.html import format_html
from django.utils.safestring import mark_safe


def format_admin_validation_error(obj, e, extra_labels=None):
    """
    Компактный форматтер django.core.exceptions.ValidationError
    для modeladmin.message_user(). Без <ul>/<li> — тема админки
    рисует их огромными плашками.
    """
    lines = [f"<strong>{obj}: не сохранено</strong>"]
    model = obj.__class__
    extra_labels = extra_labels or {}

    message_dict = getattr(e, "message_dict", None) or {"__all__": e.messages}

    for field, messages_list in message_dict.items():
        if field in extra_labels:
            field_label = extra_labels[field]
        elif field == "__all__":
            field_label = "Общая ошибка"
        else:
            try:
                field_label = model._meta.get_field(field).verbose_name.capitalize()
            except Exception:
                field_label = field

        for msg in messages_list:
            if ":" in msg and ";" in msg:
                intro, _, rest = msg.partition(":")
                items = [item.strip() for item in rest.split(";") if item.strip()]
                items_str = " &nbsp;·&nbsp; ".join(items)
                lines.append(
                    f"<u>{field_label}</u>: {intro.strip()} "
                    f"<span style='opacity:0.85;'>({items_str})</span>"
                )
            else:
                lines.append(f"<u>{field_label}</u>: {msg}")

    return format_html(
        "<div style='line-height:1.5; font-size:13px;'>{}</div>",
        mark_safe("<br>".join(lines)),
    )
