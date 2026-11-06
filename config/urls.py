from django.contrib import admin
from django.urls import include, path

from apps.core.views import dashboard, health_check

urlpatterns = [
    path("admin/", admin.site.urls),
    path("health/", health_check, name="health_check"),
    path("accounts/", include("apps.accounts.urls")),
    path("workspace/", include("apps.workspaces.urls")),
    path("", include("apps.operations.urls")),
    path("", dashboard, name="dashboard"),
]
