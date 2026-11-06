"""Business rules for the work-item lifecycle.

Views deliberately stay thin: every state transition is performed here inside
an atomic transaction, with a matching append-only audit event.
"""
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from apps.operations.models import AuditEvent, Evidence, WorkItem
from apps.workspaces.permissions import can_manage, can_review


def _membership_for(item, user):
    return user.memberships.filter(workspace_id=item.workspace_id, is_active=True).first()


def _ensure_assignee_or_manager(item, user):
    membership = _membership_for(item, user)
    if item.assigned_to_id != user.pk and not can_manage(membership):
        raise PermissionDenied("Виконувати цю задачу може лише відповідальний або адміністратор.")


def _audit(item, actor, event_type, **details):
    AuditEvent.objects.create(
        workspace_id=item.workspace_id,
        work_item=item,
        actor=actor,
        event_type=event_type,
        details=details,
    )


@transaction.atomic
def start_work_item(item: WorkItem, actor) -> WorkItem:
    locked = WorkItem.objects.select_for_update().select_related("workspace").get(pk=item.pk)
    _ensure_assignee_or_manager(locked, actor)
    if locked.status not in (WorkItem.Status.OPEN, WorkItem.Status.REJECTED):
        raise ValidationError("Почати можна лише відкриту задачу або повернуту на доопрацювання.")
    previous_status = locked.status
    locked.status = WorkItem.Status.IN_PROGRESS
    locked.review_note = ""
    locked.reviewed_at = None
    locked.reviewed_by = None
    locked.save(update_fields=("status", "review_note", "reviewed_at", "reviewed_by", "updated_at"))
    _audit(locked, actor, AuditEvent.EventType.ITEM_STARTED, previous_status=previous_status)
    return locked


@transaction.atomic
def add_evidence(item: WorkItem, actor, uploaded_file, description="") -> Evidence:
    locked = WorkItem.objects.select_for_update().get(pk=item.pk)
    _ensure_assignee_or_manager(locked, actor)
    if locked.status not in (
        WorkItem.Status.OPEN,
        WorkItem.Status.IN_PROGRESS,
        WorkItem.Status.REJECTED,
    ):
        raise ValidationError("Після надсилання на перевірку додавати файли не можна.")
    evidence = Evidence(
        workspace_id=locked.workspace_id,
        work_item=locked,
        uploaded_by=actor,
        file=uploaded_file,
        original_name=uploaded_file.name[:255],
        description=description.strip(),
    )
    evidence.save()
    _audit(
        locked,
        actor,
        AuditEvent.EventType.EVIDENCE_ADDED,
        evidence_id=evidence.pk,
        file_name=evidence.original_name,
        sha256=evidence.sha256,
    )
    return evidence


@transaction.atomic
def submit_work_item(item: WorkItem, actor) -> WorkItem:
    locked = WorkItem.objects.select_for_update().get(pk=item.pk)
    _ensure_assignee_or_manager(locked, actor)
    if locked.status != WorkItem.Status.IN_PROGRESS:
        raise ValidationError("На перевірку можна надіслати лише задачу зі статусом «У роботі».")
    if not Evidence.objects.filter(work_item=locked).exists():
        raise ValidationError("Додайте хоча б один файл-підтвердження перед надсиланням.")
    locked.status = WorkItem.Status.SUBMITTED
    locked.submitted_at = timezone.now()
    locked.save(update_fields=("status", "submitted_at", "updated_at"))
    _audit(locked, actor, AuditEvent.EventType.ITEM_SUBMITTED)
    return locked


@transaction.atomic
def review_work_item(item: WorkItem, actor, decision: str, review_note="") -> WorkItem:
    locked = WorkItem.objects.select_for_update().get(pk=item.pk)
    membership = _membership_for(locked, actor)
    if not can_review(membership):
        raise PermissionDenied("Перевіряти результати можуть власники, адміністратори та перевіряльники.")
    if locked.assigned_to_id == actor.pk:
        raise PermissionDenied("Не можна перевіряти власний результат. Призначте іншого перевіряльника.")
    if locked.status != WorkItem.Status.SUBMITTED:
        raise ValidationError("Перевіряти можна лише надіслані задачі.")
    if decision not in (WorkItem.Status.APPROVED, WorkItem.Status.REJECTED):
        raise ValidationError("Невідоме рішення перевірки.")
    note = review_note.strip()
    if decision == WorkItem.Status.REJECTED and not note:
        raise ValidationError("Для повернення на доопрацювання обов’язково вкажіть причину.")

    locked.status = decision
    locked.reviewed_at = timezone.now()
    locked.reviewed_by = actor
    locked.review_note = note
    locked.save(
        update_fields=("status", "reviewed_at", "reviewed_by", "review_note", "updated_at")
    )
    event_type = (
        AuditEvent.EventType.ITEM_APPROVED
        if decision == WorkItem.Status.APPROVED
        else AuditEvent.EventType.ITEM_REJECTED
    )
    _audit(locked, actor, event_type, review_note=note)
    return locked
