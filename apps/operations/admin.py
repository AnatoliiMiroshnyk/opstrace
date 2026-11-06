from django.contrib import admin

from apps.operations.models import AuditEvent, Evidence, Routine, WorkItem


@admin.register(Routine)
class RoutineAdmin(admin.ModelAdmin):
    list_display = ("name", "workspace", "cadence", "next_due_date", "assigned_to", "is_active")
    list_filter = ("cadence", "priority", "is_active")
    search_fields = ("name", "workspace__name", "assigned_to__email")
    readonly_fields = ("created_at", "updated_at")


class EvidenceInline(admin.TabularInline):
    model = Evidence
    extra = 0
    readonly_fields = ("workspace", "uploaded_by", "file", "original_name", "sha256", "created_at")
    can_delete = False


@admin.register(WorkItem)
class WorkItemAdmin(admin.ModelAdmin):
    list_display = ("title", "workspace", "scheduled_for", "due_date", "assigned_to", "status")
    list_filter = ("status", "priority", "due_date")
    search_fields = ("title", "workspace__name", "assigned_to__email")
    readonly_fields = (
        "workspace", "routine", "scheduled_for", "due_date", "title", "instructions",
        "assigned_to", "priority", "status", "submitted_at", "reviewed_at", "reviewed_by",
        "review_note", "created_at", "updated_at",
    )
    inlines = (EvidenceInline,)

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Evidence)
class EvidenceAdmin(admin.ModelAdmin):
    list_display = ("original_name", "work_item", "uploaded_by", "created_at")
    readonly_fields = ("workspace", "work_item", "uploaded_by", "file", "original_name", "description", "sha256", "created_at")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(AuditEvent)
class AuditEventAdmin(admin.ModelAdmin):
    list_display = ("event_type", "workspace", "work_item", "actor", "created_at")
    list_filter = ("event_type", "created_at")
    search_fields = ("workspace__name", "actor__email")
    readonly_fields = ("workspace", "work_item", "actor", "event_type", "details", "created_at")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
