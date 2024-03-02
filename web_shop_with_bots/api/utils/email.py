from django.contrib.auth.tokens import default_token_generator
from templated_mail.mail import BaseEmailMessage

from djoser import utils
from djoser.conf import settings


class MyActivationEmail(BaseEmailMessage):
    template_name = "email/my_activation.html"

    def get_context_data(self):
        # ActivationEmail can be deleted
        context = super().get_context_data()

        user = context.get("user")
        context["uid"] = utils.encode_uid(user.pk)
        context["token"] = default_token_generator.make_token(user)
        context["url"] = settings.ACTIVATION_URL.format(**context)
        return context


class MyConfirmationEmail(BaseEmailMessage):
    template_name = "email/my_confirmation.html"


class MyPasswordResetEmail(BaseEmailMessage):
    template_name = "email/my_password_reset.html"

    def get_context_data(self):
        # PasswordResetEmail can be deleted
        context = super().get_context_data()

        user = context.get("user")
        context["uid"] = utils.encode_uid(user.pk)
        context["token"] = default_token_generator.make_token(user)
        context["url"] = settings.PASSWORD_RESET_CONFIRM_URL.format(**context)
        return context


class MyPasswordChangedConfirmationEmail(BaseEmailMessage):
    template_name = "email/my_password_changed_confirmation.html"


class MyUsernameChangedConfirmationEmail(BaseEmailMessage):
    template_name = "email/my_username_changed_confirmation.html"


class MyUsernameResetEmail(BaseEmailMessage):
    template_name = "email/my_username_reset.html"

    def get_context_data(self):
        context = super().get_context_data()

        user = context.get("user")
        context["uid"] = utils.encode_uid(user.pk)
        context["token"] = default_token_generator.make_token(user)
        context["url"] = settings.USERNAME_RESET_CONFIRM_URL.format(**context)
        return context
