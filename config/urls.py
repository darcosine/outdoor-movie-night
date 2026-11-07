from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

admin.site.site_header = "Outdoor Movie Night"
admin.site.site_title = "Movie Night admin"
admin.site.index_title = "Registrations"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("manage/", include("dashboard.urls")),
    path("", include("registrations.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

handler404 = "registrations.views.page_not_found"
