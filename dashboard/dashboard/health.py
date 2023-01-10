from django.http import JsonResponse


def live(request):
    return JsonResponse({
        'live': True,
    }, status=200)


def ready(request):
    return JsonResponse({
        'ready': True,
    }, status=200)
