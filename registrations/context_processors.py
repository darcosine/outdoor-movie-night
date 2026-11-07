from django.conf import settings


def event(request):
    return {
        "event": settings.EVENT,
        "pay_rupees": settings.PAY_RUPEES,
        "reserve_rupees": settings.RESERVE_RUPEES,
        "surcharge_rupees": settings.DOOR_SURCHARGE_RUPEES,
    }
