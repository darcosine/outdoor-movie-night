from django.urls import path

from dashboard import views

app_name = "dashboard"

urlpatterns = [
    path("login/", views.staff_login, name="login"),
    path("logout/", views.staff_logout, name="logout"),
    path("", views.dashboard, name="home"),
    path("export.csv", views.export_csv, name="export"),
    path("movie/", views.edit_featured_movie, name="movie"),
    path("<int:pk>/mark-paid/", views.mark_paid, name="mark_paid"),
    path("<int:pk>/remove/", views.remove_registration, name="remove"),
]


