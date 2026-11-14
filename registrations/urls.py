from django.urls import path

from registrations import views

app_name = "registrations"

urlpatterns = [
    path("", views.home, name="home"),
    path("register/check/", views.check_reg_number, name="check_reg"),
    path("registration/<uuid:public_id>/", views.confirmation, name="confirmation"),
    path("healthz/", views.healthz, name="healthz"),
]
