from django.contrib import admin

from apps.workspaces.models import Membership, Workspace


class MembershipInline(admin.TabularInline):
    model = Membership
    extra = 0


@admin.register(Workspace)
class WorkspaceAdmin(admin.ModelAdmin):
    list_display = ("name", "created_by", "created_at")
    search_fields = ("name", "created_by__email")
    inlines = (MembershipInline,)


@admin.register(Membership)
class MembershipAdmin(admin.ModelAdmin):
    list_display = ("workspace", "user", "role", "is_active")
    list_filter = ("role", "is_active")
    search_fields = ("workspace__name", "user__email")
