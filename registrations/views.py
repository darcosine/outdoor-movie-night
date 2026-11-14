from django.db import IntegrityError, transaction
from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_http_methods
from django_ratelimit.decorators import ratelimit

from registrations.forms import RegistrationForm
from registrations.models import FeaturedMovie, Registration


@ratelimit(key="ip", rate="10/m", method="POST", block=False)
@require_http_methods(["GET", "POST"])
def home(request):
    if request.method == "POST" and getattr(request, "limited", False):
        return render(request, "registrations/rate_limited.html", status=429)

    form = RegistrationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            with transaction.atomic():
                registration = Registration.objects.create(
                    name=form.cleaned_data["name"],
                    reg_number=form.cleaned_data["reg_number"],
                    phone=form.cleaned_data["phone"],
                    status=Registration.Status.RESERVED,
                    amount_due=settings.RESERVATION_RUPEES,
                )
        except IntegrityError:
            existing = Registration.objects.get(reg_number=form.cleaned_data["reg_number"])
            return render(request, "registrations/already_registered.html", {
                "registration": existing,
                "phone_matches": existing.phone == form.cleaned_data["phone"],
            })
        return redirect("registrations:confirmation", public_id=registration.public_id)

    return render(request, "registrations/home.html", {
        "form": form,
        "featured_movie": FeaturedMovie.objects.filter(pk=1).first(),
    })


@ratelimit(key="ip", rate="30/m", method="GET", block=False)
@require_GET
def check_reg_number(request):
    if getattr(request, "limited", False):
        return HttpResponse("")
    reg_number = (request.GET.get("reg_number") or "").strip().upper()
    valid_length = len(reg_number) == 10
    valid_format = valid_length and reg_number.isascii() and reg_number.isalnum()
    taken = valid_format and Registration.objects.filter(reg_number=reg_number).exists()
    return render(request, "registrations/partials/reg_check.html", {
        "taken": taken, "valid_length": valid_length, "valid_format": valid_format,
    })


def confirmation(request, public_id):
    registration = get_object_or_404(Registration, public_id=public_id)
    return render(request, "registrations/confirmation.html", {"registration": registration})


def healthz(request):
    return HttpResponse("ok")


def page_not_found(request, exception):
    return render(request, "registrations/404.html", status=404)
