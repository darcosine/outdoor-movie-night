import csv
import logging

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.forms import AuthenticationForm
from django.db.models import Q, Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_GET, require_http_methods, require_POST
from django_ratelimit.decorators import ratelimit

from dashboard.forms import FeaturedMovieForm
from registrations.models import FeaturedMovie, Registration
from registrations.services.storage import delete_poster, store_poster

logger = logging.getLogger(__name__)


def _filtered(request):
    query = (request.GET.get("q") or "").strip()
    status = (request.GET.get("status") or "").strip()
    registrations = Registration.objects.all()
    if query:
        registrations = registrations.filter(Q(name__icontains=query) | Q(reg_number__icontains=query))
    valid_status = set(Registration.Status.values)
    if status in valid_status:
        registrations = registrations.filter(status=status)
    else:
        status = ""
    return registrations, query, status


def _counts():
    reserved = Registration.objects.filter(status=Registration.Status.RESERVED).count()
    paid = Registration.objects.filter(status=Registration.Status.PAID).count()
    return {"total": Registration.objects.count(), "reserved": reserved,
            "paid": paid,
            "reservation_value": reserved * settings.RESERVATION_RUPEES,
            "actual_value": Registration.objects.filter(
                status=Registration.Status.PAID
            ).aggregate(total=Sum("amount_paid"))["total"] or 0}


@ratelimit(key="ip", rate="5/m", method="POST", block=True)
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
            if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
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
    context = {"registrations": registrations, "q": query, "status": status,
               "statuses": Registration.Status.choices, **_counts()}
    template = "dashboard/_table.html" if request.htmx else "dashboard/dashboard.html"
    return render(request, template, context)


@staff_member_required(login_url="dashboard:login")
@require_GET
def export_csv(request):
    registrations, _, _ = _filtered(request)
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="registrations.csv"'
    writer = csv.writer(response)
    writer.writerow(["name", "reg_number", "phone", "status", "amount_due_rupees", "amount_paid_rupees", "created_at"])
    for row in registrations:
        writer.writerow([_csv_safe(row.name), _csv_safe(row.reg_number), _csv_safe(row.phone),
                         row.status, row.amount_due, row.amount_paid or "", row.created_at.isoformat()])
    return response


def _csv_safe(value):
    text = str(value)
    return "'" + text if text[:1] in {"=", "+", "-", "@"} else text


@staff_member_required(login_url="dashboard:login")
@require_POST
def mark_paid(request, pk):
    registration = get_object_or_404(Registration, pk=pk)
    amount_paid = request.POST.get("amount_paid")
    if amount_paid not in {str(settings.RESERVATION_RUPEES), str(settings.ONSPOT_RUPEES)}:
        messages.error(request, "Choose whether the payment was on-spot before marking it paid.")
        return redirect("dashboard:home")
    if registration.status != Registration.Status.PAID:
        registration.status = Registration.Status.PAID
        registration.amount_due = 0
        registration.amount_paid = int(amount_paid)
        registration.save(update_fields=["status", "amount_due", "amount_paid"])
        messages.success(request, f"Marked {registration.name} as paid (₹{amount_paid}).")
    else:
        messages.info(request, f"{registration.name} is already marked paid.")
    return redirect("dashboard:home")


@staff_member_required(login_url="dashboard:login")
@require_POST
def remove_registration(request, pk):
    registration = get_object_or_404(Registration, pk=pk)
    reg_number = registration.reg_number
    registration.delete()
    messages.success(request, f"Removed registration {reg_number}.")
    return redirect("dashboard:home")


@staff_member_required(login_url="dashboard:login")
@require_http_methods(["GET", "POST"])
def edit_featured_movie(request):
    movie = FeaturedMovie.objects.filter(pk=1).first() or FeaturedMovie(pk=1, title="", poster_image_url="")
    form = FeaturedMovieForm(request.POST or None, request.FILES or None, instance=movie)
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
