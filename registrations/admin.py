from django.contrib import admin

from registrations.models import FeaturedMovie, Payment, Registration, WebhookEvent


@admin.register(Registration)
class RegistrationAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "reg_number",
        "status",
        "amount_due",
        "phone",
        "created_at",
        "paid_at",
    )
    list_filter = ("status",)
    search_fields = ("name", "reg_number", "phone")
    readonly_fields = ("public_id", "created_at", "paid_at")


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = (
        "merchant_transaction_id",
        "registration",
        "amount",
        "state",
        "phonepe_transaction_id",
        "created_at",
    )
    list_filter = ("state",)
    search_fields = ("merchant_transaction_id", "phonepe_transaction_id")
    readonly_fields = ("raw_response", "created_at")


@admin.register(WebhookEvent)
class WebhookEventAdmin(admin.ModelAdmin):
    list_display = ("event_id", "created_at")
    readonly_fields = ("event_id", "payload", "created_at")

@admin.register(FeaturedMovie)
class FeaturedMovieAdmin(admin.ModelAdmin):
    list_display = ("title", "updated_at")
    readonly_fields = ("updated_at",)
