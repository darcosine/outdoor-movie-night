from django.conf import settings


def event(request):
    return {
        "event": settings.EVENT,
        "reservation_rupees": settings.RESERVATION_RUPEES,
        "onspot_rupees": settings.ONSPOT_RUPEES,
    }
