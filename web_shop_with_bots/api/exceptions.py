from rest_framework.exceptions import ErrorDetail


class CustomHttp400(Exception):
    def __init__(self, detail, code):
        self.detail = ErrorDetail(detail, code)
