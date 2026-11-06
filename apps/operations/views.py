from django.contrib import messages
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.operations.forms import EvidenceForm, ReviewForm, RoutineForm
from apps.operations.models import AuditEvent, Evidence, Routine, WorkItem
from apps.operations.services import (
    add_evidence,
    review_work_item,
    start_work_item,
    submit_work_item,
)
from apps.workspaces.permissions import can_manage, can_review, manager_required, reviewer_required, workspace_member_required


def _visible_items(request):
    queryset = WorkItem.objects.filter(workspace=request.workspace)
    if not can_review(request.membership):
        queryset = queryset.filter(assigned_to=request.user)
    return queryset


def _get_item(request, pk):
    item = get_object_or_404(
        _visible_items(request).select_related(
            "routine", "assigned_to", "reviewed_by", "workspace"
        ),
        pk=pk,
    )
    return item


@workspace_member_required
def routine_list(request):
    routines = Routine.objects.filter(workspace=request.workspace).select_related(
        "assigned_to", "created_by"
    )
    if not can_manage(request.membership):
        routines = routines.filter(assigned_to=request.user)
    return render(request, "operations/routine_list.html", {"routines": routines})


@manager_required
@transaction.atomic
def routine_create(request):
    form = RoutineForm(request.POST or None, workspace=request.workspace)
    if request.method == "POST" and form.is_valid():
        routine = form.save(commit=False)
        routine.created_by = request.user
        routine.full_clean()
        routine.save()
        AuditEvent.objects.create(
            workspace=request.workspace,
            actor=request.user,
            event_type=AuditEvent.EventType.ROUTINE_CREATED,
            details={"routine_id": routine.pk, "routine_name": routine.name},
        )
        messages.success(request, "Регламент створено. Завдання буде згенеровано планувальником.")
        return redirect("operations:routines")
    return render(request, "operations/routine_form.html", {"form": form})


@manager_required
@transaction.atomic
def routine_update(request, pk):
    routine = get_object_or_404(Routine, pk=pk, workspace=request.workspace)
    form = RoutineForm(request.POST or None, instance=routine, workspace=request.workspace)
    if request.method == "POST" and form.is_valid():
        updated = form.save(commit=False)
        updated.full_clean()
        updated.save()
        AuditEvent.objects.create(
            workspace=request.workspace,
            actor=request.user,
            event_type=AuditEvent.EventType.ROUTINE_UPDATED,
            details={"routine_id": routine.pk, "routine_name": routine.name},
        )
        messages.success(request, "Регламент оновлено.")
        return redirect("operations:routines")
    return render(
        request,
        "operations/routine_form.html",
        {"form": form, "editing": True, "routine": routine},
    )


@workspace_member_required
def work_item_list(request):
    items = _visible_items(request).select_related("routine", "assigned_to")
    status = request.GET.get("status", "")
    valid_statuses = {choice for choice, _label in WorkItem.Status.choices}
    if status in valid_statuses:
        items = items.filter(status=status)
    mine = request.GET.get("mine") == "1"
    if mine:
        items = items.filter(assigned_to=request.user)
    return render(
        request,
        "operations/work_item_list.html",
        {"items": items, "selected_status": status, "mine": mine, "status_choices": WorkItem.Status.choices},
    )


@workspace_member_required
def work_item_detail(request, pk):
    item = _get_item(request, pk)
    evidence_form = EvidenceForm()
    review_form = ReviewForm()
    return render(
        request,
        "operations/work_item_detail.html",
        {
            "item": item,
            "evidence": item.evidence_files.select_related("uploaded_by"),
            "events": item.audit_events.select_related("actor"),
            "evidence_form": evidence_form,
            "review_form": review_form,
            "can_manage_item": can_manage(request.membership),
            "can_review_item": can_review(request.membership)
            and item.assigned_to_id != request.user.pk,
            "is_assignee": item.assigned_to_id == request.user.pk,
        },
    )


@workspace_member_required
@require_POST
def work_item_start(request, pk):
    item = _get_item(request, pk)
    try:
        start_work_item(item, request.user)
        messages.success(request, "Виконання розпочато.")
    except (ValidationError, PermissionDenied) as exc:
        messages.error(request, str(exc))
    return redirect("operations:item_detail", pk=pk)


@workspace_member_required
@require_POST
def work_item_evidence(request, pk):
    item = _get_item(request, pk)
    form = EvidenceForm(request.POST, request.FILES)
    if form.is_valid():
        try:
            add_evidence(
                item,
                request.user,
                form.cleaned_data["file"],
                form.cleaned_data.get("description", ""),
            )
            messages.success(request, "Підтвердження додано.")
        except (ValidationError, PermissionDenied) as exc:
            messages.error(request, str(exc))
    else:
        messages.error(request, "Не вдалося завантажити файл. Перевірте формат і розмір.")
    return redirect("operations:item_detail", pk=pk)


@workspace_member_required
@require_POST
def work_item_submit(request, pk):
    item = _get_item(request, pk)
    try:
        submit_work_item(item, request.user)
        messages.success(request, "Задачу надіслано на перевірку.")
    except (ValidationError, PermissionDenied) as exc:
        messages.error(request, str(exc))
    return redirect("operations:item_detail", pk=pk)


@reviewer_required
@require_POST
def work_item_review(request, pk):
    item = _get_item(request, pk)
    form = ReviewForm(request.POST)
    if form.is_valid():
        try:
            review_work_item(
                item,
                request.user,
                form.cleaned_data["decision"],
                form.cleaned_data["review_note"],
            )
            messages.success(request, "Рішення перевірки збережено.")
        except (ValidationError, PermissionDenied) as exc:
            messages.error(request, str(exc))
    else:
        messages.error(request, "Перевірте рішення та коментар.")
    return redirect("operations:item_detail", pk=pk)


@workspace_member_required
def evidence_download(request, pk, evidence_id):
    item = _get_item(request, pk)
    evidence = get_object_or_404(
        Evidence.objects.filter(workspace=request.workspace, work_item=item), pk=evidence_id
    )
    try:
        handle = evidence.file.open("rb")
    except (FileNotFoundError, OSError):
        raise Http404("Файл не знайдено.") from None
    response = FileResponse(handle, as_attachment=True, filename=evidence.original_name)
    response["X-Content-Type-Options"] = "nosniff"
    return response
