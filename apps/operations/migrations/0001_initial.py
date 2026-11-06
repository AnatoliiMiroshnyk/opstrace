import django.core.validators
import django.db.models.deletion
import apps.operations.models
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("workspaces", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Routine",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=160)),
                ("instructions", models.TextField(blank=True)),
                ("cadence", models.CharField(choices=[("daily", "Щодня"), ("weekly", "Щотижня"), ("monthly", "Щомісяця"), ("quarterly", "Щокварталу"), ("yearly", "Щороку")], max_length=12)),
                ("next_due_date", models.DateField(db_index=True)),
                ("priority", models.CharField(choices=[("low", "Низький"), ("normal", "Звичайний"), ("high", "Високий"), ("critical", "Критичний")], default="normal", max_length=10)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("assigned_to", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="assigned_routines", to=settings.AUTH_USER_MODEL)),
                ("created_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="created_routines", to=settings.AUTH_USER_MODEL)),
                ("workspace", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="routines", to="workspaces.workspace")),
            ],
            options={"ordering": ["next_due_date", "name"]},
        ),
        migrations.AddIndex(
            model_name="routine",
            index=models.Index(fields=["workspace", "is_active", "next_due_date"], name="op_routine_ws_active_due_idx"),
        ),
        migrations.CreateModel(
            name="WorkItem",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("scheduled_for", models.DateField()),
                ("due_date", models.DateField(db_index=True)),
                ("title", models.CharField(max_length=160)),
                ("instructions", models.TextField(blank=True)),
                ("priority", models.CharField(choices=[("low", "Низький"), ("normal", "Звичайний"), ("high", "Високий"), ("critical", "Критичний")], default="normal", max_length=10)),
                ("status", models.CharField(choices=[("open", "Відкрита"), ("in_progress", "У роботі"), ("submitted", "На перевірці"), ("approved", "Прийнята"), ("rejected", "Потрібне доопрацювання")], db_index=True, default="open", max_length=16)),
                ("submitted_at", models.DateTimeField(blank=True, null=True)),
                ("reviewed_at", models.DateTimeField(blank=True, null=True)),
                ("review_note", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("assigned_to", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="work_items", to=settings.AUTH_USER_MODEL)),
                ("reviewed_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="reviewed_work_items", to=settings.AUTH_USER_MODEL)),
                ("routine", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="work_items", to="operations.routine")),
                ("workspace", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="work_items", to="workspaces.workspace")),
            ],
            options={"ordering": ["due_date", "-priority", "title"]},
        ),
        migrations.AddConstraint(
            model_name="workitem",
            constraint=models.UniqueConstraint(fields=("routine", "scheduled_for"), name="unique_routine_occurrence"),
        ),
        migrations.AddIndex(
            model_name="workitem",
            index=models.Index(fields=["workspace", "status", "due_date"], name="operations_worksp_33e5c4_idx"),
        ),
        migrations.AddIndex(
            model_name="workitem",
            index=models.Index(fields=["workspace", "assigned_to", "status"], name="operations_worksp_6219c9_idx"),
        ),
        migrations.CreateModel(
            name="Evidence",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("file", models.FileField(upload_to=apps.operations.models.evidence_upload_to, validators=[django.core.validators.FileExtensionValidator(allowed_extensions=("pdf", "png", "jpg", "jpeg", "webp")), apps.operations.models.validate_evidence_size])),
                ("original_name", models.CharField(max_length=255)),
                ("description", models.CharField(blank=True, max_length=240)),
                ("sha256", models.CharField(blank=True, editable=False, max_length=64)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("uploaded_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="uploaded_evidence", to=settings.AUTH_USER_MODEL)),
                ("work_item", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="evidence_files", to="operations.workitem")),
                ("workspace", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="evidence_files", to="workspaces.workspace")),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="AuditEvent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("event_type", models.CharField(choices=[("routine_created", "Створено регламент"), ("routine_updated", "Оновлено регламент"), ("item_generated", "Згенеровано завдання"), ("item_started", "Розпочато виконання"), ("evidence_added", "Додано підтвердження"), ("item_submitted", "Надіслано на перевірку"), ("item_approved", "Результат прийнято"), ("item_rejected", "Результат відхилено")], max_length=24)),
                ("details", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("actor", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="audit_events", to=settings.AUTH_USER_MODEL)),
                ("work_item", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="audit_events", to="operations.workitem")),
                ("workspace", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="audit_events", to="workspaces.workspace")),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.AddIndex(
            model_name="auditevent",
            index=models.Index(fields=["workspace", "created_at"], name="op_audit_ws_created_idx"),
        ),
    ]
