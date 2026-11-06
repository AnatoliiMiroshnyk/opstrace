class WorkspaceMiddleware:
    """Attach the active workspace and membership to each authenticated request.

    The workspace ID in the session is never trusted on its own: membership is
    re-checked against the database on every request.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.workspace = None
        request.membership = None

        if request.user.is_authenticated:
            memberships = (
                request.user.memberships.filter(is_active=True)
                .select_related("workspace")
                .order_by("joined_at")
            )
            selected_id = request.session.get("workspace_id")
            membership = memberships.filter(workspace_id=selected_id).first()
            if membership is None:
                membership = memberships.first()
                if membership:
                    request.session["workspace_id"] = membership.workspace_id
                else:
                    request.session.pop("workspace_id", None)
            if membership:
                request.membership = membership
                request.workspace = membership.workspace

        return self.get_response(request)
