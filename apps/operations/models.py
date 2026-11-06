import hashlib
import uuid
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from django.db import models

from apps.workspaces.models import Workspace


ALLOWED_EVIDENCE_EXTENSIONS = ("pdf", "png", "jpg", "jpeg", "webp")


def evidence_upload_to(instance, filename):
    suffix = Path(filename).suffix.lower()
    return f"evidence/{instance.workspace_id}/{uuid.uuid4().hex}{suffix}"


def validate_evidence_size(value):
    max_size = getattr(settings, "MAX_EVIDENCE_SIZE", 10 * 1024 * 1024)
    if value.size > max_size:
        raise ValidationError("Файл завеликий. Максимальний розмір — 10 МБ.")


class Routine(models.Model):
    class Cadence(models.TextChoices):
        DAILY = "daily", "Щодня"
        WEEKLY = "weekly", "Щотижня"
        MONTHLY = "monthly", "Щомісяця"
        QUARTERLY = "quarterly", "Щокварталу"
        YEARLY = "yearly", "Щороку"

    class Priority(models.TextChoices):
        LOW = "low", "Низький"
        NORMAL = "normal", "Звичайний"
        HIGH = "high", "Високий"
        CRITICAL = "critical", "Критичний"

    workspace = models.ForeignKey(
        Workspace, on_delete=models.CASCADE, related_name="routines"
    )
    name = models.CharField(max_length=160)
    instructions = models.TextField(blank=True)
    cadence = models.CharField(max_length=12, choices=Cadence.choices)
    next_due_date = models.DateField(db_index=True)
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="assigned_routines",
    )
    priority = models.CharField(
        max_length=10, choices=Priority.choices, default=Priority.NORMAL
    )
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_routines",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["next_due_date", "name"]
        indexes = [models.Index(fields=("workspace", "is_active", "next_due_date"), name="op_routine_ws_active_due_idx")]

    def clean(self):
        super().clean()
        if self.workspace_id and self.assigned_to_id:
            from apps.workspaces.models import Membership

            if not Membership.objects.filter(
                workspace_id=self.workspace_id,
                user_id=self.assigned_to_id,
                is_active=True,
            ).exists():
                raise ValidationError(
                    {"assigned_to": "Відповідальний має бути активним учасником простору."}
                )

    def __str__(self):
        return self.name


class WorkItem(models.Model):
    class Status(models.TextChoices):
        OPEN = "open", "Відкрита"
        IN_PROGRESS = "in_progress", "У роботі"
        SUBMITTED = "submitted", "На перевірці"
        APPROVED = "approved", "Прийнята"
        REJECTED = "rejected", "Потрібне доопрацювання"

    workspace = models.ForeignKey(
        Workspace, on_delete=models.CASCADE, related_name="work_items"
    )
    routine = models.ForeignKey(
        Routine, on_delete=models.PROTECT, related_name="work_items"
    )
    scheduled_for = models.DateField()
    due_date = models.DateField(db_index=True)
    title = models.CharField(max_length=160)
    instructions = models.TextField(blank=True)
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="work_items",
    )
    priority = models.CharField(
        max_length=10, choices=Routine.Priority.choices, default=Routine.Priority.NORMAL
    )
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.OPEN, db_index=True
    )
    submitted_at = models.DateTimeField(null=True, blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_work_items",
    )
    review_note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["due_date", "-priority", "title"]
        constraints = [
            models.UniqueConstraint(
                fields=("routine", "scheduled_for"), name="unique_routine_occurrence"
            )
        ]
        indexes = [
            models.Index(fields=("workspace", "status", "due_date"), name="operations_worksp_33e5c4_idx"),
            models.Index(fields=("workspace", "assigned_to", "status"), name="operations_worksp_6219c9_idx"),
        ]

    def clean(self):
        super().clean()
        if self.routine_id and self.workspace_id:
            if self.routine.workspace_id != self.workspace_id:
                raise ValidationError("Регламент і завдання мають належати одному простору.")

    @property
    def is_overdue(self):
        from django.utils import timezone

        return self.due_date < timezone.localdate() and self.status != self.Status.APPROVED

    def __str__(self):
        return f"{self.title} — {self.scheduled_for:%Y-%m-%d}"


class Evidence(models.Model):
    workspace = models.ForeignKey(
        Workspace, on_delete=models.CASCADE, related_name="evidence_files"
    )
    work_item = models.ForeignKey(
        WorkItem, on_delete=models.CASCADE, related_name="evidence_files"
    )
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="uploaded_evidence",
    )
    file = models.FileField(
        upload_to=evidence_upload_to,
        validators=[
            FileExtensionValidator(allowed_extensions=ALLOWED_EVIDENCE_EXTENSIONS),
            validate_evidence_size,
        ],
    )
    original_name = models.CharField(max_length=255)
    description = models.CharField(max_length=240, blank=True)
    sha256 = models.CharField(max_length=64, blank=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def clean(self):
        super().clean()
        if self.work_item_id and self.workspace_id:
            if self.work_item.workspace_id != self.workspace_id:
                raise ValidationError("Файл і завдання мають належати одному простору.")

    def save(self, *args, **kwargs):
        if self.file and not self.sha256:
            digest = hashlib.sha256()
            for chunk in self.file.chunks():
                digest.update(chunk)
            self.sha256 = digest.hexdigest()
            self.file.seek(0)
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.original_name


class ImmutableAuditQuerySet(models.QuerySet):
    def update(self, **kwargs):
        raise ValidationError("Події аудиту не можна змінювати через QuerySet.")

    def delete(self):
        raise ValidationError("Події аудиту не можна видаляти через QuerySet.")

    def bulk_create(self, *args, **kwargs):
        raise ValidationError("Для журналу аудиту використовуйте звичайне створення записів.")

    def bulk_update(self, *args, **kwargs):
        raise ValidationError("Події аудиту не можна оновлювати пакетно.")


class ImmutableAuditManager(models.Manager.from_queryset(ImmutableAuditQuerySet)):
    pass


class AuditEvent(models.Model):
    objects = ImmutableAuditManager()

    class EventType(models.TextChoices):
        ROUTINE_CREATED = "routine_created", "Створено регламент"
        ROUTINE_UPDATED = "routine_updated", "Оновлено регламент"
        ITEM_GENERATED = "item_generated", "Згенеровано завдання"
        ITEM_STARTED = "item_started", "Розпочато виконання"
        EVIDENCE_ADDED = "evidence_added", "Додано підтвердження"
        ITEM_SUBMITTED = "item_submitted", "Надіслано на перевірку"
        ITEM_APPROVED = "item_approved", "Результат прийнято"
        ITEM_REJECTED = "item_rejected", "Результат відхилено"

    workspace = models.ForeignKey(
        Workspace, on_delete=models.CASCADE, related_name="audit_events"
    )
    work_item = models.ForeignKey(
        WorkItem,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_events",
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_events",
    )
    event_type = models.CharField(max_length=24, choices=EventType.choices)
    details = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=("workspace", "created_at"), name="op_audit_ws_created_idx")]

    def save(self, *args, **kwargs):
        if self.pk:
            raise ValidationError("Події аудиту не можна змінювати.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("Події аудиту не можна видаляти.")

    def __str__(self):
        return f"{self.get_event_type_display()} ({self.created_at:%Y-%m-%d %H:%M})"
