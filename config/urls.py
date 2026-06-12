from django.conf import settings
from django.contrib import admin
from django.urls import include, path, re_path
from django.views.static import serve

from core import views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("core.urls")),
]

# Uploaded art slides are served by the app (low traffic; mount MEDIA_ROOT in Docker).
urlpatterns += [
    re_path(
        r"^media/(?P<path>.*)$",
        serve,
        {"document_root": settings.MEDIA_ROOT},
    ),
]

handler404 = "core.views.page_not_found"
