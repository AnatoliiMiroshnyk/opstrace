def workspace_context(request):
    memberships = None
    if request.user.is_authenticated:
        memberships = (
            request.user.memberships.filter(is_active=True)
            .select_related("workspace")
            .order_by("workspace__name")
        )
    return {
        "current_workspace": getattr(request, "workspace", None),
        "current_membership": getattr(request, "membership", None),
        "available_memberships": memberships,
    }
