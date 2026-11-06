from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_http_methods, require_POST

from apps.operations.models import Routine, WorkItem
from apps.workspaces.forms import TeamMemberForm
from apps.workspaces.models import Membership
from apps.workspaces.permissions import manager_required


@login_required
@require_POST
def switch_workspace(request):
    workspace_id = request.POST.get("workspace_id")
    membership = (
        Membership.objects.filter(
            user=request.user,
            workspace_id=workspace_id,
            is_active=True,
        )
        .select_related("workspace")
        .first()
    )
    if membership is None:
        return HttpResponseBadRequest("Недійсний робочий простір.")

    request.session["workspace_id"] = membership.workspace_id
    messages.success(request, f"Активний простір: {membership.workspace.name}")
    redirect_to = request.POST.get("next", "")
    if url_has_allowed_host_and_scheme(
        redirect_to,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return redirect(redirect_to)
    return redirect("dashboard")


@manager_required
@require_http_methods(["GET", "POST"])
def team_list(request):
    form = TeamMemberForm(request.POST or None, workspace=request.workspace)
    if request.method == "POST" and form.is_valid():
        membership = form.save()
        messages.success(request, f"{membership.user.email} додано до робочого простору.")
        return redirect("workspaces:team")
    memberships = request.workspace.memberships.select_related("user").all()
    return render(
        request,
        "workspaces/team.html",
        {"form": form, "memberships": memberships},
    )


@manager_required
@require_POST
def deactivate_member(request, membership_id):
    membership = get_object_or_404(
        request.workspace.memberships.select_related("user"), pk=membership_id
    )
    if membership.role == Membership.Role.OWNER:
        raise PermissionDenied("Власника простору не можна деактивувати.")
    has_active_routines = Routine.objects.filter(
        workspace=request.workspace, assigned_to=membership.user, is_active=True
    ).exists()
    has_pending_work = WorkItem.objects.filter(
        workspace=request.workspace, assigned_to=membership.user
    ).exclude(status=WorkItem.Status.APPROVED).exists()
    if has_active_routines or has_pending_work:
        messages.error(
            request,
            "Спочатку призначте активні регламенти та незавершені завдання іншому учаснику.",
        )
        return redirect("workspaces:team")
    membership.is_active = False
    membership.save(update_fields=("is_active",))
    messages.success(request, f"Доступ для {membership.user.email} вимкнено.")
    return redirect("workspaces:team")
