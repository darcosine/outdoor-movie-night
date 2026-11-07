import csv
import logging

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.forms import AuthenticationForm
from django.db import transaction
from django.db.models import Q, Sum
from django.db.models.functions import Coalesce
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from registrations.models import FeaturedMovie, Payment, Registration, new_merchant_transaction_id
from dashboard.forms import FeaturedMovieForm
from registrations.services.storage import delete_id_card, delete_poster, store_poster

logger = logging.getLogger(__name__)


def _filtered(request):
    query = (request.GET.get("q") or "").strip()
    status = (request.GET.get("status") or "").strip()
    registrations = Registration.objects.all().prefetch_related("payments")
    if query:
        registrations = registrations.filter(
            Q(name__icontains=query) | Q(reg_number__icontains=query)
        )
    valid_status = set(Registration.Status.values)
    if status in valid_status:
        registrations = registrations.filter(status=status)
    else:
        status = ""
    return registrations, query, status


def _counts():
    paid_paise = Payment.objects.filter(state=Payment.State.COMPLETED).aggregate(
        total=Coalesce(Sum("amount"), 0)
    )["total"]
    reserved = Registration.objects.filter(status=Registration.Status.RESERVED).count()
    return {
        "total": Registration.objects.count(),
        "paid": Registration.objects.filter(status=Registration.Status.PAID).count(),
        "reserved": reserved,
        "pending": Registration.objects.filter(status=Registration.Status.PENDING_PAYMENT).count(),
        "expected_revenue": paid_paise // 100 + reserved * settings.RESERVE_RUPEES,
    }


def staff_login(request):
    if request.user.is_authenticated and request.user.is_staff:
        return redirect("dashboard:home")
    form = AuthenticationForm(request, data=request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.get_user()
        if not user.is_staff:
            form.add_error(None, "This page is for event staff only.")
        else:
            login(request, user)
            next_url = request.GET.get("next", "")
            if next_url and url_has_allowed_host_and_scheme(
                next_url,
                allowed_hosts={request.get_host()},
                require_https=request.is_secure(),
            ):
                return redirect(next_url)
            return redirect("dashboard:home")
    return render(request, "dashboard/login.html", {"form": form})


@require_POST
def staff_logout(request):
    logout(request)
    return redirect("dashboard:login")


@staff_member_required(login_url="dashboard:login")
@require_http_methods(["GET"])
def dashboard(request):
    registrations, query, status = _filtered(request)
    context = {
        "registrations": registrations,
        "q": query,
        "status": status,
        "statuses": Registration.Status.choices,
        "can_mark_paid": timezone.localdate() < settings.EVENT_DATE,
        **_counts(),
    }
    template = "dashboard/_table.html" if request.htmx else "dashboard/dashboard.html"
    return render(request, template, context)


@staff_member_required(login_url="dashboard:login")
@require_GET
def export_csv(request):
    registrations, query, status = _filtered(request)
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="registrations.csv"'
    writer = csv.writer(response)
    writer.writerow(
        [
            "name",
            "reg_number",
            "phone",
            "status",
            "amount_due_rupees",
            "amount_paid_rupees",
            "transaction_id",
            "created_at",
            "paid_at",
            "id_card_image_url",
        ]
    )
    for registration in registrations:
        writer.writerow(
            [
                _csv_safe(registration.name),
                _csv_safe(registration.reg_number),
                registration.phone,
                registration.status,
                registration.amount_due,
                registration.amount_paid_rupees(),
                _csv_safe(registration.transaction_reference()),
                registration.created_at.isoformat(),
                registration.paid_at.isoformat() if registration.paid_at else "",
                registration.id_card_image_url,
            ]
        )
    return response


def _csv_safe(value):
    text = str(value)
    if text[:1] in {"=", "+", "-", "@"}:
        return "'" + text
    return text


@staff_member_required(login_url="dashboard:login")
@require_POST
def mark_paid(request, pk):
    with transaction.atomic():
        registration = get_object_or_404(_lock_registrations(), pk=pk)
        if registration.status == Registration.Status.PAID:
            messages.info(request, f"{registration.reg_number} is already marked paid.")
        elif timezone.localdate() >= settings.EVENT_DATE:
            messages.error(request, "Manual payment updates closed on the event date.")
        elif registration.status not in {
            Registration.Status.RESERVED,
            Registration.Status.PENDING_PAYMENT,
            Registration.Status.FAILED,
        }:
            messages.error(request, "This registration cannot be manually marked paid.")
        else:
            is_reservation = registration.status == Registration.Status.RESERVED
            amount_rupees = settings.RESERVE_RUPEES if is_reservation else settings.PAY_RUPEES
            Payment.objects.filter(
                registration=registration, state=Payment.State.PENDING
            ).delete()
            Payment.objects.create(
                registration=registration,
                merchant_transaction_id="STAFF" + new_merchant_transaction_id()[:30],
                amount=amount_rupees * 100,
                state=Payment.State.COMPLETED,
                raw_response={"source": "staff_manual", "staff_user_id": request.user.pk},
            )
            registration.status = Registration.Status.PAID
            registration.amount_due = 0
            registration.paid_at = timezone.now()
            registration.save(update_fields=["status", "amount_due", "paid_at"])
            messages.success(
                request, f"Marked {registration.name} as paid (₹{amount_rupees})."
            )
    return redirect("dashboard:home")


def _lock_registrations():
    from django.db import connection

    queryset = Registration.objects.all()
    if connection.vendor == "postgresql":
        return queryset.select_for_update()
    return queryset






@staff_member_required(login_url="dashboard:login")
@require_POST
def remove_registration(request, pk):
    with transaction.atomic():
        registration = get_object_or_404(_lock_registrations(), pk=pk)
        reg_number = registration.reg_number
        try:
            delete_id_card(registration.id_card_image_url)
        except Exception:
            logger.exception("Could not delete ID-card asset for registration %s", reg_number)
            messages.error(
                request,
                "The ID-card image could not be removed, so the registration was left unchanged.",
            )
            return redirect("dashboard:home")
        Payment.objects.filter(registration=registration).delete()
        registration.delete()
    messages.success(request, f"Removed registration {reg_number} and its payment records.")
    return redirect("dashboard:home")


@staff_member_required(login_url="dashboard:login")
@require_http_methods(["GET", "POST"])
def edit_featured_movie(request):
    movie = FeaturedMovie.objects.filter(pk=1).first()
    if movie is None:
        movie = FeaturedMovie(pk=1, title="", poster_image_url="")

    form = FeaturedMovieForm(
        request.POST or None,
        request.FILES or None,
        instance=movie,
    )
    if request.method == "POST" and form.is_valid():
        uploaded = form.cleaned_data.get("poster_upload")
        old_poster_url = movie.poster_image_url
        new_poster_url = None
        if uploaded:
            try:
                new_poster_url = store_poster(uploaded)
            except Exception:
                logger.exception("Featured movie poster upload failed")
                form.add_error("poster_upload", "The poster could not be saved. Check image storage settings.")
            else:
                movie.poster_image_url = new_poster_url
        if not form.errors:
            movie.title = form.cleaned_data["title"]
            try:
                movie.save()
            except Exception:
                if new_poster_url:
                    try:
                        delete_poster(new_poster_url)
                    except Exception:
                        logger.exception("Could not clean up an unused featured poster")
                raise
            if old_poster_url and new_poster_url and old_poster_url != new_poster_url:
                try:
                    delete_poster(old_poster_url)
                except Exception:
                    logger.exception("Could not delete the replaced featured poster")
            messages.success(request, "Featured movie updated on the student page.")
            return redirect("dashboard:home")

    return render(request, "dashboard/movie_form.html", {"form": form, "movie": movie})
