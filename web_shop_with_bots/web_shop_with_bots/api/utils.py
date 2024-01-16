from rest_framework import status
from rest_framework.response import Response


def check_existance_create_delete(model, method, response,
                                  serializer=None, instance=None,
                                  **kwargs):
    """
    Метод используется для создания/удаления Many-To-Many связей.
    В зависимости от передаваемого метода POST/DELETE проводит проверку перед
    созданием или удалением объекта и возвращает ответ,
    в зависимости от требуемой формы ответа response и сериализатора.

    Создание, метод POST:
    Проверяет отсутствие экземпляра класса в переданной модели по
    параметрам, передаваемым в **kwargs, чтобы избежать дублирования при
    создании. В зависимости от значения response (response/redirect) может
    сформировать Response с данными сериализатора, указанного в serializer.

    Удаление, метод DELETE:
    Проверяет существование экземпляра класса в переданной модели по
    параметрам, передаваемым в **kwargs, чтобы убедиться, что его можно
    удалить. Возвращает Response объект с данными статуса.
    """
    if method == 'POST':
        if model.objects.filter(**kwargs).exists():
            return Response('Данная запись уже существует.',
                            status=status.HTTP_400_BAD_REQUEST)
        model.objects.create(**kwargs)
        if response == 'response':
            return Response(serializer(instance).data)
        return 'redirect'

    if not model.objects.filter(**kwargs).exists():
        return Response('Такой записи нет, удаление невозможно.',
                        status=status.HTTP_400_BAD_REQUEST)
    model.objects.filter(**kwargs).delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


if __name__ == '__main__':
    pass
