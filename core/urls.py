from django.urls import path

from . import views

app_name = "core"

urlpatterns = [
    path("sw.js", views.service_worker_unregister, name="service_worker_unregister"),
    path("api/tv/display-config/", views.tv_display_config, name="tv_display_config"),
    path("api/tv/widgets/weather/", views.tv_widget_weather, name="tv_widget_weather"),
    path("api/tv/widgets/earthquakes/", views.tv_widget_earthquake, name="tv_widget_earthquake"),
    path("api/tv/widgets/wealth/", views.tv_widget_wealth, name="tv_widget_wealth"),
    path("api/tv/widgets/binance/", views.tv_widget_binance, name="tv_widget_binance"),
    path("missing", views.missing_page, name="missing"),
    path("missing/", views.missing_page, name="missing_slash"),
    path("wait/", views.wait_page, name="wait"),
    path("updating/", views.updating_page, name="updating"),
    path("updating.html", views.wait_page, name="updating_html"),
    path("", views.tv_dashboard, name="tv_dashboard"),
    path("health/", views.health, name="health"),
    path("favicon.ico", views.favicon, name="favicon"),
]
