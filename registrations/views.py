import json

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.db import IntegrityError, transaction
from django.http import Http404, HttpResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_http_methods, require_POST
from django_ratelimit.decorators import ratelimit

from registrations.forms import RegistrationForm
from registrations.models import FeaturedMovie, Payment, Registration, new_merchant_transaction_id
from registrations.services.phonepe import (
    InvalidCallback,
    PhonePeError,
    initiate_payment,
    process_callback,
    remember_mock_outcome,
    x_verify,
)
from registrations.services.storage import store_id_card

_SCREENSHOT = "Take a screenshot of this page as proof of registration."


def _friendly_duplicate(request, registration, phone):
    return render(
        request,
        "registrations/already_registered.html",
        {
            "registration": registration,
            "phone_matches": registration.phone == phone,
        },
    )


def _start_payment(request, registration):
    payment = Payment.objects.create(
        registration=registration,
        merchant_transaction_id=new_merchant_transaction_id(),
        amount=settings.PAY_PAISE,
        state=Payment.State.PENDING,
    )
    try:
        url = initiate_payment(payment)
    except PhonePeError:
        # Failed initiation attempts are not retained as payment records.
        payment.delete()
        registration.status = Registration.Status.PENDING_PAYMENT
        registration.save(update_fields=["status"])
        return redirect("registrations:confirmation", public_id=registration.public_id)
    request.session[f"payment_registration:{payment.merchant_transaction_id}"] = str(
        registration.public_id
    )
    return redirect(url)

@ratelimit(key="ip", rate="10/m", method="POST", block=False)
@require_http_methods(["GET", "POST"])
def home(request):
    if request.method == "POST" and getattr(request, "limited", False):
        return render(request, "registrations/rate_limited.html", status=429)

    form = RegistrationForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        choice = request.POST.get("choice")
        if choice not in {"pay", "reserve"}:
            form.add_error(None, "Choose Pay now or Reserve a seat.")
        else:
            existing = Registration.objects.filter(
                reg_number=form.cleaned_data["reg_number"]
            ).first()
            if existing:
                return _friendly_duplicate(request, existing, form.cleaned_data["phone"])
            try:
                image_url = store_id_card(form.cleaned_data["id_card"])
            except ImproperlyConfigured:
                form.add_error(
                    None,
                    "ID card storage is not configured yet. Tell the organisers.",
                )
            else:
                status = (
                    Registration.Status.RESERVED
                    if choice == "reserve"
                    else Registration.Status.PENDING_PAYMENT
                )
                amount_due = settings.RESERVE_RUPEES if choice == "reserve" else settings.PAY_RUPEES
                try:
                    with transaction.atomic():
                        registration = Registration.objects.create(
                            name=form.cleaned_data["name"],
                            reg_number=form.cleaned_data["reg_number"],
                            phone=form.cleaned_data["phone"],
                            id_card_image_url=image_url,
                            status=status,
                            amount_due=amount_due,
                        )
                except IntegrityError:
                    existing = Registration.objects.get(reg_number=form.cleaned_data["reg_number"])
                    return _friendly_duplicate(request, existing, form.cleaned_data["phone"])
                if choice == "reserve":
                    return redirect("registrations:confirmation", public_id=registration.public_id)
                return _start_payment(request, registration)

    return render(
        request,
        "registrations/home.html",
        {
            "form": form,
            "featured_movie": FeaturedMovie.objects.filter(pk=1).first(),
        },
    )


@ratelimit(key="ip", rate="30/m", method="GET", block=False)
@require_GET
def check_reg_number(request):
    if getattr(request, "limited", False):
        return HttpResponse("")
    reg_number = (request.GET.get("reg_number") or "").strip().upper()
    valid_length = len(reg_number) == 10
    valid_format = valid_length and reg_number.isascii() and reg_number.isalnum()
    taken = valid_format and Registration.objects.filter(reg_number=reg_number).exists()
    return render(
        request,
        "registrations/partials/reg_check.html",
        {"taken": taken, "valid_length": valid_length, "valid_format": valid_format},
    )


def confirmation(request, public_id):
    registration = get_object_or_404(Registration, public_id=public_id)
    return render(
        request,
        "registrations/confirmation.html",
        {"registration": registration, "screenshot_message": _SCREENSHOT},
    )


@ratelimit(key="ip", rate="10/m", method="POST", block=False)
@require_POST
def retry_payment(request, public_id):
    if getattr(request, "limited", False):
        return render(request, "registrations/rate_limited.html", status=429)
    registration = get_object_or_404(Registration, public_id=public_id)
    if not registration.is_open_for_payment:
        return redirect("registrations:confirmation", public_id=registration.public_id)
    registration.amount_due = settings.PAY_RUPEES
    registration.status = Registration.Status.PENDING_PAYMENT
    registration.save(update_fields=["amount_due", "status"])
    return _start_payment(request, registration)


@ratelimit(key="ip", rate="10/m", method="POST", block=False)
@require_POST
def switch_to_reserve(request, public_id):
    if getattr(request, "limited", False):
        return render(request, "registrations/rate_limited.html", status=429)
    registration = get_object_or_404(Registration, public_id=public_id)
    if registration.status == Registration.Status.PAID:
        return redirect("registrations:confirmation", public_id=registration.public_id)
    if registration.status != Registration.Status.RESERVED:
        registration.status = Registration.Status.RESERVED
        registration.amount_due = settings.RESERVE_RUPEES
        registration.save(update_fields=["status", "amount_due"])
    return redirect("registrations:confirmation", public_id=registration.public_id)


def _callback_body(request) -> str:
    posted = request.POST.get("response")
    if posted:
        return posted
    if "application/json" in (request.content_type or ""):
        try:
            data = json.loads(request.body.decode() or "{}")
        except json.JSONDecodeError:
            return ""
        return data.get("response") or ""
    return ""


@csrf_exempt
@require_POST
def phonepe_callback(request):
    """Server-to-server callback. The browser return URL is a different view."""
    try:
        process_callback(_callback_body(request), request.headers.get("X-VERIFY", ""))
    except InvalidCallback:
        return HttpResponse(status=400)
    except PhonePeError:
        return HttpResponse(status=502)
    return HttpResponse("ok")


@require_GET
def payment_return(request):
    """Landing page after checkout. Reads the database; it does not trust the query string."""
    merchant_transaction_id = request.GET.get("transactionId") or request.GET.get(
        "merchantTransactionId"
    ) or ""
    payment = (
        Payment.objects.filter(merchant_transaction_id=merchant_transaction_id)
        .select_related("registration")
        .first()
    )
    if payment is None:
        public_id = request.session.pop(f"payment_registration:{merchant_transaction_id}", None)
        if public_id:
            return redirect("registrations:confirmation", public_id=public_id)
        return render(request, "registrations/payment_wait.html", {"payment": None}, status=404)
    request.session.pop(f"payment_registration:{merchant_transaction_id}", None)
    registration = payment.registration
    if registration.status in {Registration.Status.PAID, Registration.Status.RESERVED}:
        return redirect("registrations:confirmation", public_id=registration.public_id)
    return render(request, "registrations/payment_wait.html", {"payment": payment})


@require_GET
def payment_poll(request, public_id):
    registration = get_object_or_404(Registration, public_id=public_id)
    if registration.status == Registration.Status.PAID:
        response = HttpResponse("")
        response["HX-Redirect"] = reverse(
            "registrations:confirmation", args=[registration.public_id]
        )
        return response
    if registration.status == Registration.Status.RESERVED:
        response = HttpResponse("")
        response["HX-Redirect"] = reverse(
            "registrations:confirmation", args=[registration.public_id]
        )
        return response
    return render(
        request,
        "registrations/partials/payment_poll.html",
        {"registration": registration},
    )


@require_http_methods(["GET", "POST"])
def mock_checkout(request, merchant_transaction_id):
    if not settings.PHONEPE_MOCK:
        raise Http404()
    payment = get_object_or_404(
        Payment.objects.select_related("registration"),
        merchant_transaction_id=merchant_transaction_id,
    )
    if request.method == "POST":
        outcome = request.POST.get("outcome")
        if outcome not in {"success", "failure"}:
            return HttpResponseBadRequest("unknown outcome")
        remember_mock_outcome(payment.merchant_transaction_id, outcome)
        import base64

        state = "COMPLETED" if outcome == "success" else "FAILED"
        code = "PAYMENT_SUCCESS" if outcome == "success" else "PAYMENT_ERROR"
        payload = {
            "success": outcome == "success",
            "code": code,
            "message": "mock callback",
            "data": {
                "merchantId": settings.PHONEPE_MERCHANT_ID,
                "merchantTransactionId": payment.merchant_transaction_id,
                "transactionId": f"MOCK{payment.merchant_transaction_id[:12]}",
                "amount": settings.PAY_PAISE,
                "state": state,
            },
        }
        encoded = base64.b64encode(json.dumps(payload).encode()).decode()
        try:
            callback_result = process_callback(encoded, x_verify(encoded))
        except PhonePeError:
            return HttpResponse(status=502)
        if callback_result == "failed":
            request.session.pop(f"payment_registration:{payment.merchant_transaction_id}", None)
            return redirect("registrations:confirmation", public_id=payment.registration.public_id)
        return redirect(
            reverse("registrations:payment_return")
            + f"?transactionId={payment.merchant_transaction_id}"
        )
    return render(request, "registrations/mock_checkout.html", {"payment": payment, "amount_rupees": payment.amount // 100})


def healthz(request):
    return HttpResponse("ok")


def page_not_found(request, exception):
    return render(request, "registrations/404.html", status=404)




