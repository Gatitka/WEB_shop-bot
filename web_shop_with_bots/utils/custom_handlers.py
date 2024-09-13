from django.http import JsonResponse


def custom_500(request):
    response = JsonResponse({'error': 'Server error (500)'})
    response.status_code = 500
    return response


def custom_404(request, exception):
    response = JsonResponse({'error': 'Not found (404)'})
    response.status_code = 404
    return response


def custom_403(request, exception):
    response = JsonResponse({'error': 'Permission denied (403)'})
    response.status_code = 403
    return response


def custom_400(request, exception):
    response = JsonResponse({'error': 'Bad request (400)'})
    response.status_code = 400
    return response
