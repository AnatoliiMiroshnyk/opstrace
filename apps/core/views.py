from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone

from apps.operations.models import WorkItem
from apps.workspaces.permissions import can_review


def health_check(_request):
    """Minimal liveness endpoint; infrastructure should separately monitor the DB."""
    return JsonResponse({"status": "ok", "service": "opstrace"})


@login_required
def dashboard(request):
    if request.workspace is None:
        return render(request, "core/no_workspace.html", status=403)

    queryset = WorkItem.objects.filter(workspace=request.workspace)
    if not can_review(request.membership):
        queryset = queryset.filter(assigned_to=request.user)

    today = timezone.localdate()
    counts = queryset.aggregate(
        total=Count("id"),
        overdue=Count("id", filter=Q(due_date__lt=today) & ~Q(status="approved")),
        in_progress=Count("id", filter=Q(status="in_progress")),
        submitted=Count("id", filter=Q(status="submitted")),
        approved=Count("id", filter=Q(status="approved")),
    )
    upcoming = (
        queryset.exclude(status="approved")
        .filter(due_date__gte=today)
        .select_related("assigned_to", "routine")
        .order_by("due_date", "priority")[:8]
    )
    overdue_items = (
        queryset.exclude(status="approved")
        .filter(due_date__lt=today)
        .select_related("assigned_to", "routine")
        .order_by("due_date")[:6]
    )
    needs_review = (
        queryset.filter(status="submitted")
        .exclude(assigned_to=request.user)
        .select_related("assigned_to", "routine")
        .order_by("submitted_at")[:6]
        if can_review(request.membership)
        else WorkItem.objects.none()
    )
    return render(
        request,
        "core/dashboard.html",
        {
            "counts": counts,
            "upcoming": upcoming,
            "overdue_items": overdue_items,
            "needs_review": needs_review,
            "today": today,
        },
    )
