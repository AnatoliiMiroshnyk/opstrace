from django.urls import path

from apps.workspaces import views

app_name = "workspaces"

urlpatterns = [
    path("switch/", views.switch_workspace, name="switch"),
    path("team/", views.team_list, name="team"),
    path("team/<int:membership_id>/deactivate/", views.deactivate_member, name="deactivate_member"),
]
