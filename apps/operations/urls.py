from django.urls import path

from apps.operations import views

app_name = "operations"

urlpatterns = [
    path("routines/", views.routine_list, name="routines"),
    path("routines/new/", views.routine_create, name="routine_create"),
    path("routines/<int:pk>/edit/", views.routine_update, name="routine_update"),
    path("work-items/", views.work_item_list, name="items"),
    path("work-items/<int:pk>/", views.work_item_detail, name="item_detail"),
    path("work-items/<int:pk>/start/", views.work_item_start, name="item_start"),
    path("work-items/<int:pk>/evidence/", views.work_item_evidence, name="item_evidence"),
    path("work-items/<int:pk>/submit/", views.work_item_submit, name="item_submit"),
    path("work-items/<int:pk>/review/", views.work_item_review, name="item_review"),
    path(
        "work-items/<int:pk>/evidence/<int:evidence_id>/download/",
        views.evidence_download,
        name="evidence_download",
    ),
]
