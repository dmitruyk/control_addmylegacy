from django.urls import path

from . import views

app_name = "core"

urlpatterns = [
    path("sw.js", views.service_worker_unregister, name="service_worker_unregister"),
    path("missing", views.missing_page, name="missing"),
    path("missing/", views.missing_page, name="missing_slash"),
    path("wait/", views.wait_page, name="wait"),
    path("updating/", views.updating_page, name="updating"),
    path("updating.html", views.wait_page, name="updating_html"),
    path("", views.tv_dashboard, name="tv_dashboard"),
    path("health/", views.health, name="health"),
    path("favicon.ico", views.favicon, name="favicon"),
]
