from django.contrib import admin

from registrations.models import FeaturedMovie, Registration


@admin.register(Registration)
class RegistrationAdmin(admin.ModelAdmin):
    list_display = ("name", "reg_number", "status", "amount_due", "amount_paid", "phone", "created_at")
    list_filter = ("status",)
    search_fields = ("name", "reg_number", "phone")
    readonly_fields = ("public_id", "name", "reg_number", "phone", "status", "amount_due", "amount_paid", "created_at")


@admin.register(FeaturedMovie)
class FeaturedMovieAdmin(admin.ModelAdmin):
    list_display = ("title", "updated_at")
    readonly_fields = ("updated_at",)
