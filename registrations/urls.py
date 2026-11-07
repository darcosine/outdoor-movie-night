from django.urls import path

from registrations import views

app_name = "registrations"

urlpatterns = [
    path("", views.home, name="home"),
    path("register/check/", views.check_reg_number, name="check_reg"),
    path("registration/<uuid:public_id>/", views.confirmation, name="confirmation"),
    path("registration/<uuid:public_id>/retry/", views.retry_payment, name="retry"),
    path("registration/<uuid:public_id>/reserve/", views.switch_to_reserve, name="switch_reserve"),
    path("registration/<uuid:public_id>/poll/", views.payment_poll, name="payment_poll"),
    path("payments/callback/", views.phonepe_callback, name="callback"),
    path("payments/return/", views.payment_return, name="payment_return"),
    path(
        "payments/mock/<str:merchant_transaction_id>/",
        views.mock_checkout,
        name="mock_checkout",
    ),
    path("healthz/", views.healthz, name="healthz"),
]
